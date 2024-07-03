import logging
import pandas as pd
import numpy as np
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select 
from db import get_db
from models import User, UserPersona, DynamicItem, DynamicItemPriority, DynamicUserFeed, Activity, PlaylistSession
from pydantic import BaseModel
from celery_config import make_celery
from recommendation import fetch_recommendations
from data_processing import fetch_data, normalize, svd_reconstruct
from fastapi.encoders import jsonable_encoder
from recommendation import fetch_recommendations_for_all_users

def convert_numpy_types(obj):
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

logger = logging.getLogger(__name__)
app = FastAPI()
# celery = make_celery(app)

# celery.conf.beat_schedule = {
#     'update-recommendations-every-night': {
#         'task': 'celery_config.update_recommendations',
#         'schedule': crontab(hour=0, minute=0),
#     },
# }

class RateGameRequest(BaseModel):
    user_id: int
    game_id: int
    rating: int

@app.post("/fetch_playlist_recommendations/{user_id}")
async def fetch_playlist_recommendations_endpoint(user_id: int, db: AsyncSession = Depends(get_db)):
    try:
        game_recommendations, playlist_recommendations = await fetch_playlist_recommendations(user_id, db)
        return {"game_recommendations": game_recommendations, "playlist_recommendations": playlist_recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recommendations/{user_id}")
async def get_recommendations(user_id: int, db: AsyncSession = Depends(get_db)):
    recommendations = await fetch_recommendations(user_id, db)
    return {"recommendations": recommendations}

@app.post("/populate_dynamic_items")
async def populate_items_endpoint(db: AsyncSession = Depends(get_db)):
    await populate_dynamic_items(db)
    return {"message": "Dynamic items populated"}

@app.post("/populate_dynamic_item_priority")
async def populate_priority_endpoint(db: AsyncSession = Depends(get_db)):
    await populate_dynamic_item_priority(db)
    return {"message": "Dynamic item priorities populated"}

@app.post("/generate_user_feed")
async def generate_feed_endpoint(db: AsyncSession = Depends(get_db)):
    await generate_user_feed(db)
    return {"message": "User feeds generated"}

@app.post("/update_playlist_recommendations")
async def update_playlist_recommendations_endpoint(db: AsyncSession = Depends(get_db)):
    try:
        await update_playlist_recommendations(db)
        return {"message": "Playlist recommendations updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def fetch_recommendations(user_id: int, db: AsyncSession):
    data = await fetch_data(db)
    
    # Log the structure of each DataFrame
    logger.info("Data fetched: %s", data.keys())
    logger.info("Game session columns: %s", data['game_session'].columns)
    logger.info("Activity columns: %s", data['activity'].columns)

    # Check if 'user_id' and 'game_id' columns exist in each DataFrame
    if 'user_id' not in data['game_session'].columns or 'game_id' not in data['game_session'].columns:
        logger.error("'user_id' or 'game_id' column missing in game_session DataFrame")
        return []

    if data['activity'].empty or 'user_id' not in data['activity'].columns or 'target_id' not in data['activity'].columns:
        logger.warning("'user_id' or 'target_id' column missing in activity DataFrame or the DataFrame is empty")
        activity_df = pd.DataFrame(columns=['user_id', 'target_id', 'engagement'])
    else:
        activity_df = data['activity'].groupby(['user_id', 'target_id']).agg({
            'timestamp': 'count'
        }).reset_index().rename(columns={'timestamp': 'engagement'})

    # Aggregate data to ensure unique index and column combinations
    game_session_df = data['game_session'].groupby(['user_id', 'game_id']).agg({
        'session_total_time': 'sum',
        'session_total_score': 'mean'
    }).reset_index()

    logger.info("Aggregated game session data: %s", game_session_df.head())
    logger.info("Aggregated activity data: %s", activity_df.head())

    # Convert Timedelta to seconds
    if 'session_total_time' in game_session_df.columns:
        game_session_df['session_total_time'] = game_session_df['session_total_time'].dt.total_seconds()

    # Ensure all matrices have the same shape
    user_ids = list(set(game_session_df['user_id']).union(activity_df['user_id']))
    game_ids = list(set(game_session_df['game_id']).union(activity_df['target_id']))

    play_count_matrix = game_session_df.pivot(index='user_id', columns='game_id', values='session_total_time').reindex(index=user_ids, columns=game_ids, fill_value=0).values
    engagement_matrix = activity_df.pivot(index='user_id', columns='target_id', values='engagement').reindex(index=user_ids, columns=game_ids, fill_value=0).values

    normalized_play_count = normalize(play_count_matrix)
    normalized_engagement = normalize(engagement_matrix)

    reconstructed_play_count = svd_reconstruct(normalized_play_count)
    reconstructed_engagement = svd_reconstruct(normalized_engagement)

    if reconstructed_play_count.size == 0:
        reconstructed_play_count = np.zeros_like(reconstructed_engagement)
    if reconstructed_engagement.size == 0:
        reconstructed_engagement = np.zeros_like(reconstructed_play_count)

    weights = [0.5, 0.5]  # Adjust weights accordingly
    combined_matrix = (weights[0] * reconstructed_play_count + weights[1] * reconstructed_engagement)

    recommendations = []
    for i, user in enumerate(user_ids):
        user_recommendations = combined_matrix[i]
        top_games = user_recommendations.argsort()[::-1][:10]  # Get top 10 recommendations
        for game_id in top_games:
            recommendations.append({"user_id": user, "game_id": game_ids[game_id]})

    return recommendations

async def update_rating(user_id: int, game_id: int, rating: int, db: AsyncSession):
    await db.execute(
        "INSERT INTO reviews (user_id, game_id, rating) VALUES (:user_id, :game_id, :rating) "
        "ON CONFLICT (user_id, game_id) DO UPDATE SET rating = :rating",
        {'user_id': user_id, 'game_id': game_id, 'rating': rating}
    )
    await db.commit()

async def populate_dynamic_items(db: AsyncSession):
    # Fetch activities
    activities = await db.execute(select(Activity))
    activities = activities.scalars().all()
    
    # Fetch recommendations
    recommendations = await fetch_recommendations_for_all_users(db)
    
    # Fetch ads (if any, otherwise define statically)
    ads = [{"item_type": "ad", "content": {"ad_content": "Buy now!"}}] * 10  # Example static ads
    
    # Insert into dynamic_item table
    items = activities + recommendations + ads
    for item in items:
        new_item = DynamicItem(item_type=item["item_type"], content=item["content"])
        db.add(new_item)
    await db.commit()

async def populate_dynamic_item_priority(db: AsyncSession):
    items = await db.execute(select(DynamicItem))
    items = items.scalars().all()
    users = await db.execute(select(User))
    users = users.scalars().all()
    
    for item in items:
        for user in users:
            # Calculate priority score (example calculation)
            priority_score = calculate_priority(item, user)
            new_priority = DynamicItemPriority(item_id=item.item_id, user_id=user.id, priority_score=priority_score)
            db.add(new_priority)
    await db.commit()

def calculate_priority(item, user):
    # Example priority calculation logic
    if item.item_type == "activity":
        return 10
    elif item.item_type == "recommendation":
        return 5
    elif item.item_type == "ad":
        return 1
    return 0

async def generate_user_feed(db: AsyncSession):
    users = await db.execute(select(User))
    users = users.scalars().all()
    
    for user in users:
        feed_items = await generate_feed_for_user(user.id, db)
        for item in feed_items:
            new_feed = DynamicUserFeed(user_id=user.id, item_id=item.item_id, feed_timestamp=datetime.utcnow())
            db.add(new_feed)
    await db.commit()

async def generate_feed_for_user(user_id, db):
    activities = await db.execute(
        select(DynamicItem).where(DynamicItem.item_type == "activity").order_by(desc(DynamicItemPriority.priority_score)).limit(6)
    )
    activities = activities.scalars().all()
    
    recommendations = await db.execute(
        select(DynamicItem).where(DynamicItem.item_type == "recommendation").order_by(desc(DynamicItemPriority.priority_score)).limit(2)
    )
    recommendations = recommendations.scalars().all()
    
    ads = await db.execute(
        select(DynamicItem).where(DynamicItem.item_type == "ad").order_by(desc(DynamicItemPriority.priority_score)).limit(1)
    )
    ads = ads.scalars().all()
    
    # Example combining logic: 3 activities, 1 recommendation, 1 ad
    feed_items = []
    for i in range(0, len(activities), 3):
        feed_items.extend(activities[i:i+3])
        if recommendations:
            feed_items.append(recommendations.pop(0))
        if ads and i % 6 == 0:  # Add an ad every 6 activities
            feed_items.append(ads.pop(0))
    
    return feed_items

async def update_playlist_recommendations(db: AsyncSession):
    data = await fetch_data(db)

    playlist_play_count_matrix = data['playlist_session'].pivot(index='user_id', columns='playlist_id', values='completed').fillna(0).values

    # Normalize and apply SVD to the matrix
    normalized_play_count = normalize(playlist_play_count_matrix)
    reconstructed_play_count = svd_reconstruct(normalized_play_count)

    # Generate recommendations based on reconstructed play counts
    recommendations = []
    user_ids = data['playlist_session']['user_id'].unique()
    playlist_ids = data['playlist_session']['playlist_id'].unique()

    for user_index, user_id in enumerate(user_ids):
        user_recommendations = []
        for playlist_index, playlist_id in enumerate(playlist_ids):
            score = reconstructed_play_count[user_index, playlist_index]
            user_recommendations.append((user_id, playlist_id, score))
        user_recommendations.sort(key=lambda x: x[2], reverse=True)
        recommendations.extend(user_recommendations[:5])  # Get top 5 recommendations for each user

    # Insert recommendations into dynamic_item and dynamic_item_priority tables
    for rec in recommendations:
        user_id, playlist_id, score = rec
        dynamic_item = DynamicItem(item_type='playlist_recommendation', content={"playlist_id": playlist_id})
        db.add(dynamic_item)
        await db.flush()  # Flush to get the primary key of the dynamic_item

        dynamic_item_priority = DynamicItemPriority(item_id=dynamic_item.item_id, user_id=user_id, priority_score=score)
        db.add(dynamic_item_priority)

    await db.commit()

async def fetch_playlist_recommendations(user_id, db: AsyncSession):
    data = await fetch_data(db)

    # Debug print statements
    print("Fetched data from the database")
    print("Data keys:", data.keys())

    try:
        # Check if 'user_id' and 'game_id' columns exist
        for key in data:
            print(f"Columns in {key}:", data[key].columns)

        if 'user_id' not in data['game_session'].columns or 'game_id' not in data['game_session'].columns:
            raise ValueError("'user_id' or 'game_id' column missing in game_session DataFrame")
        if 'user_id' not in data['favorite'].columns or 'game_id' not in data['favorite'].columns:
            raise ValueError("'user_id' or 'game_id' column missing in favorite DataFrame")
        if 'user_id' not in data['comment'].columns or 'game_id' not in data['comment'].columns:
            raise ValueError("'user_id' or 'game_id' column missing in comment DataFrame")

        user_game_sessions = data['game_session'][data['game_session']['user_id'] == user_id]
        user_favorites = data['favorite'][data['favorite']['user_id'] == user_id]
        user_comments = data['comment'][data['comment']['user_id'] == user_id]

        user_playlist_sessions = pd.DataFrame(columns=['user_id', 'playlist_id'])
        if 'user_id' in data['playlist_session'].columns and 'playlist_id' in data['playlist_session'].columns:
            user_playlist_sessions = data['playlist_session'][(data['playlist_session']['user_id'] == user_id) & (data['playlist_session']['completed'] == True)]

        # Debug print statements
        print("User game sessions:", user_game_sessions)
        print("User favorites:", user_favorites)
        print("User comments:", user_comments)
        print("User playlist sessions:", user_playlist_sessions)

        relevant_playlists = []
        if not user_playlist_sessions.empty:
            relevant_playlists = user_playlist_sessions['playlist_id'].unique()

        relevant_games = pd.concat([user_game_sessions['game_id'], user_favorites['game_id'], user_comments['game_id']]).unique()

        # Debugging relevant games and playlists
        print("Relevant games:", relevant_games)
        print("Relevant playlists:", relevant_playlists)

        # Aggregate game_session data to ensure uniqueness
        game_session_agg = data['game_session'].groupby(['user_id', 'game_id']).agg({'session_total_time': 'sum'}).reset_index()

        # Convert Timedelta to total seconds
        game_session_agg['session_total_time'] = game_session_agg['session_total_time'].dt.total_seconds()

        # Debugging aggregated data
        print("Aggregated game session data:", game_session_agg)

        # Pivot the aggregated data
        game_matrix = game_session_agg.pivot(index='user_id', columns='game_id', values='session_total_time').fillna(0).values

        # Debugging matrix shapes after pivot
        print("Game session matrix shape after pivot:", game_matrix.shape)

        normalized_game_matrix = normalize(game_matrix)

        # Debugging normalized matrix shapes
        print("Normalized game matrix shape:", normalized_game_matrix.shape)

        reconstructed_game_matrix = svd_reconstruct(normalized_game_matrix)

        # Debugging reconstructed matrix shapes
        print("Reconstructed game matrix shape:", reconstructed_game_matrix.shape)

        game_recommendations = []
        playlist_recommendations = []
        user_indices = game_session_agg['user_id'].unique()
        game_ids = game_session_agg['game_id'].unique()
        playlist_ids = data['playlist_session']['playlist_id'].unique() if 'playlist_id' in data['playlist_session'].columns else []

        if user_id in user_indices:
            user_index = np.where(user_indices == user_id)[0][0]

            for game_index, game_id in enumerate(game_ids):
                score = reconstructed_game_matrix[user_index, game_index]
                game_recommendations.append((user_id, game_id, score))

            # Ensure relevant playlists are handled properly
            if len(relevant_playlists) > 0:
                for playlist_id in relevant_playlists:
                    playlist_recommendations.append((user_id, playlist_id, 1))  # Arbitrary score since we're just identifying relevance

            game_recommendations.sort(key=lambda x: x[2], reverse=True)
            playlist_recommendations.sort(key=lambda x: x[2], reverse=True)

            top_game_recommendations = game_recommendations[:5]
            top_playlist_recommendations = playlist_recommendations[:5]

            # Convert numpy types to Python types
            top_game_recommendations = [(convert_numpy_types(a), convert_numpy_types(b), convert_numpy_types(c)) for a, b, c in top_game_recommendations]
            top_playlist_recommendations = [(convert_numpy_types(a), convert_numpy_types(b), convert_numpy_types(c)) for a, b, c in top_playlist_recommendations]

            return top_game_recommendations, top_playlist_recommendations
        else:
            return [], []
    except Exception as e:
        print(f"Error during recommendation computation: {e}")
        raise


# @app.post("/rate_game")
# async def rate_game(request: RateGameRequest, db: AsyncSession = Depends(get_db)):
#     await update_rating(request.user_id, request.game_id, request.rating, db)
#     update_recommendations_for_user.delay(request.user_id)
#     return {"message": "Rating received"}

# @celery.task
# def update_recommendations_for_user(user_id: int):
#     from db import SessionLocal
#     from recommendation import fetch_recommendations

#     async def update_user_recommendations():
#         async with SessionLocal() as session:
#             recommendations = await fetch_recommendations(user_id, session)
#             await session.execute(
#                 "DELETE FROM dynamic_user_feed WHERE user_id = :user_id",
#                 {'user_id': user_id}
#             )
#             for item in recommendations:
#                 await session.execute(
#                     "INSERT INTO dynamic_user_feed (user_id, item_id, feed_timestamp) VALUES (:user_id, :item_id, NOW())",
#                     {'user_id': user_id, 'item_id': item['item_id']}
#                 )
#             await session.commit()

#     import asyncio
#     asyncio.run(update_user_recommendations())

# @celery.task
# def update_recommendations():
#     from db import SessionLocal
#     from models import User
#     from recommendation import fetch_recommendations

#     async def update_all_user_recommendations():
#         async with SessionLocal() as session:
#             result = await session.execute("SELECT id FROM users")
#             user_ids = result.scalars().all()
#             for user_id in user_ids:
#                 recommendations = await fetch_recommendations(user_id, session)
#                 await session.execute(
#                     "DELETE FROM dynamic_user_feed WHERE user_id = :user_id",
#                     {'user_id': user_id}
#                 )
#                 for item in recommendations:
#                     await session.execute(
#                         "INSERT INTO dynamic_user_feed (user_id, item_id, feed_timestamp) VALUES (:user_id, :item_id, NOW())",
#                         {'user_id': user_id, 'item_id': item['item_id']}
#                     )
#             await session.commit()

#     import asyncio
#     asyncio.run(update_all_user_recommendations())
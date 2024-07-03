from data_processing import fetch_data, normalize, svd_reconstruct
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

async def fetch_recommendations(user_id: int, db: AsyncSession):
    df = await fetch_data(db)
    play_count_matrix = df.pivot(index='user_id', columns='game_id', values='play_count').fillna(0).values
    rating_matrix = df.pivot(index='user_id', columns='game_id', values='rating').fillna(0).values
    engagement_matrix = df.pivot(index='user_id', columns='game_id', values='engagement').fillna(0).values

    normalized_play_count = normalize(play_count_matrix)
    normalized_ratings = normalize(rating_matrix)
    normalized_engagement = normalize(engagement_matrix)

    reconstructed_play_count = svd_reconstruct(normalized_play_count)
    reconstructed_ratings = svd_reconstruct(normalized_ratings)
    reconstructed_engagement = svd_reconstruct(normalized_engagement)

    weights = [0.4, 0.3, 0.3]
    combined_matrix = (weights[0] * reconstructed_play_count +
                       weights[1] * reconstructed_ratings +
                       weights[2] * reconstructed_engagement)

    user_recommendations = combined_matrix[user_id].tolist()
    return [{'item_id': idx, 'priority_score': score} for idx, score in enumerate(user_recommendations)]

async def fetch_recommendations_for_all_users(db: AsyncSession):
    data = await fetch_data(db)

    # Ensure data contains DataFrames
    if not all(isinstance(df, pd.DataFrame) for df in data.values()):
        raise ValueError("All values in the data dictionary must be pandas DataFrames")
    
    game_sessions_df = data['game_session']
    
    if game_sessions_df.empty:
        return {}

    play_count_matrix = game_sessions_df.pivot(index='user_id', columns='game_id', values='play_count').fillna(0).values
    rating_matrix = game_sessions_df.pivot(index='user_id', columns='game_id', values='rating').fillna(0).values
    engagement_matrix = game_sessions_df.pivot(index='user_id', columns='game_id', values='engagement').fillna(0).values

    normalized_play_count = normalize(play_count_matrix)
    normalized_ratings = normalize(rating_matrix)
    normalized_engagement = normalize(engagement_matrix)

    reconstructed_play_count = svd_reconstruct(normalized_play_count)
    reconstructed_ratings = svd_reconstruct(normalized_ratings)
    reconstructed_engagement = svd_reconstruct(normalized_engagement)

    weights = [0.4, 0.3, 0.3]
    combined_matrix = (weights[0] * reconstructed_play_count +
                       weights[1] * reconstructed_ratings +
                       weights[2] * reconstructed_engagement)

    all_user_recommendations = {}
    user_ids = game_sessions_df['user_id'].unique()
    
    for idx, user_id in enumerate(user_ids):
        user_recommendations = combined_matrix[idx].tolist()
        all_user_recommendations[user_id] = [{'item_id': item_id, 'priority_score': score} for item_id, score in enumerate(user_recommendations)]

    return all_user_recommendations
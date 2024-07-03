from data_processing import fetch_data, normalize, svd_reconstruct
from sqlalchemy.ext.asyncio import AsyncSession

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
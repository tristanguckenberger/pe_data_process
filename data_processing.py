import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Activity, Comment, Favorite, Follow, GameSession, PlaylistSession, PlaylistUserActivity
from scipy.sparse.linalg import svds

async def fetch_data(db: AsyncSession):
    activity_result = await db.execute(select(Activity))
    activities = activity_result.scalars().all()

    comment_result = await db.execute(select(Comment))
    comments = comment_result.scalars().all()

    favorite_result = await db.execute(select(Favorite))
    favorites = favorite_result.scalars().all()

    follow_result = await db.execute(select(Follow))
    follows = follow_result.scalars().all()

    game_session_result = await db.execute(select(GameSession))
    game_sessions = game_session_result.scalars().all()

    # review_result = await db.execute(select(Review))
    # reviews = review_result.scalars().all()

    playlist_session_result = await db.execute(select(PlaylistSession))
    playlist_sessions = playlist_session_result.scalars().all()

    playlist_user_activity_result = await db.execute(select(PlaylistUserActivity))
    playlist_user_activities = playlist_user_activity_result.scalars().all()

    activity_df = pd.DataFrame([activity.__dict__ for activity in activities])
    comment_df = pd.DataFrame([comment.__dict__ for comment in comments])
    favorite_df = pd.DataFrame([favorite.__dict__ for favorite in favorites])
    follow_df = pd.DataFrame([follow.__dict__ for follow in follows])
    game_session_df = pd.DataFrame([game_session.__dict__ for game_session in game_sessions])
    # review_df = pd.DataFrame([review.__dict__ for review in reviews])
    playlist_session_df = pd.DataFrame([session.__dict__ for session in playlist_sessions])
    playlist_user_activity_df = pd.DataFrame([activity.__dict__ for activity in playlist_user_activities])

    return {
        "activity": activity_df,
        "comment": comment_df,
        "favorite": favorite_df,
        "follow": follow_df,
        "game_session": game_session_df,
        # "review": review_df,
        "playlist_session": playlist_session_df,
        "playlist_user_activity": playlist_user_activity_df
    }

def normalize(matrix):
    norm_matrix = matrix.astype(np.float32)
    for i in range(len(norm_matrix)):
        row_max = max(norm_matrix[i])
        if row_max > 0:
            norm_matrix[i] = norm_matrix[i] / row_max
    return norm_matrix

def svd_reconstruct(matrix, k=2):
    if matrix.size == 0:
        return np.zeros(matrix.shape)
    
    min_dim = min(matrix.shape)
    k = min(k, min_dim - 1)  # Ensure k is less than the smallest dimension of the matrix
    k = max(k, 1)  # Ensure k is at least 1

    try:
        U, sigma, Vt = svds(matrix, k=k)
        sigma = np.diag(sigma)
        return np.dot(np.dot(U, sigma), Vt)
    except Exception as e:
        print(f"Exception occurred during SVD reconstruction: {e}")
        return np.zeros(matrix.shape)
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db
from models import User

async def get_current_user(db: AsyncSession = Depends(get_db)):
    # This is a placeholder, replace with your actual authentication mechanism
    user = await db.execute(select(User).where(User.username == "test_user"))
    user = user.scalars().first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return user
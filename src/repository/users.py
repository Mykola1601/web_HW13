from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.database.models import User
from src.schemas.auth import UserModel


async def get_user_by_mail(mail : str, db:AsyncSession=Depends(get_db)):
    query = select(User).filter_by(mail=mail)
    user = await db.execute(query)
    user = user.scalar_one_or_none()
    return user

async def create_user(body:UserModel, db:AsyncSession=Depends(get_db) ):
    avatar = None
    try:
        ...
        # g = Gravatar(body.mail)
        # avatar = g.teg_image()
    except Exception as err:
        print(err)

    new_user = User(**body.model_dump(), avatar = avatar)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def update_token(user:User, token:str | None, db:AsyncSession):
    user.refresh_token = token
    await db.commit()


async def confirmed_email(email: str, db: AsyncSession) -> None:
    user = await get_user_by_mail(email, db)
    user.confirmed = True
    await db.commit()


async def update_avatar_url(email:str, url:str|None, db:AsyncSession)-> User:
    user = await get_user_by_mail(email, db)
    user.avatar = url
    await db.commit()
    await db.refresh(user)
    return user









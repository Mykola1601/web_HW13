
import pickle
import cloudinary
import cloudinary.uploader

from typing import List
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from sqlalchemy.orm import Session
from src.database.db import get_db
from src.schemas.auth import UserResponse
from src.repository import contacts as repository_contacts
from src.database.models import Role, User
from src.services.auth import auth_service
from fastapi_limiter.depends import RateLimiter
from src.conf.config import config
from src.repository import users as repository_users


router = APIRouter(prefix='/users', tags=["users"])
cloudinary.config(cloud_name =config.CLOUD_NAME, api_key=config.CLOUD_API_KEY, 
                    api_secret=config.CLOUD_API_SECRET, secure=True)


@router.get("/me", response_model=UserResponse, dependencies=[Depends(RateLimiter(times=2, seconds=5))])
async  def get_current_user(user:User=Depends(auth_service.get_current_user)):
    return user


@router.patch("/avatar", response_model=UserResponse,
                dependencies=[Depends(RateLimiter(times=2, seconds=5))])
async  def get_current_photo(file:UploadFile=File(), user:User=Depends(auth_service.get_current_user),
                            db: Session = Depends(get_db)):
    public_id = f"python/{user.mail}"
    result = cloudinary.uploader.upload(file.file, public_id=public_id, owerite=True)
    result_url = cloudinary.CloudinaryImage(public_id).build_url(width=250, heigh=250, crop="fill", version=result.get("version"))
    user = await repository_users.update_avatar_url(user.mail, result_url, db)
    auth_service.cache.set(user.mail, pickle.dumps(user))
    auth_service.cache.expire(user.mail, time=600)
    return user








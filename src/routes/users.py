from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from src.database.db import get_db
from src.schemas.auth import UserResponse
from src.repository import contacts as repository_contacts
from src.database.models import Role, User
from src.services.auth import auth_service
from fastapi_limiter.depends import RateLimiter


router = APIRouter(prefix='/users', tags=["users"])

@router.get("/me", response_model=UserResponse, dependencies=[Depends(RateLimiter(times=2, seconds=5))])
async  def get_current_user(user:User=Depends(auth_service.get_current_user)):
    return user











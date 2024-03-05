from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from fastapi_limiter.depends import RateLimiter
from fastapi.security import OAuth2PasswordRequestForm, HTTPAuthorizationCredentials, HTTPBearer
from fastapi import APIRouter, HTTPException, Depends, status, Path, BackgroundTasks, Request, Response
from src.database.db import get_db
from src.services.mail import send_email
from src.services.auth import auth_service 
from src.repository import users as repository_users
from src.schemas.auth import UserResponse, TokenModel, UserModel, RequestEmail


router = APIRouter(prefix='/auth', tags=["auth"])
get_refresh_token = HTTPBearer()


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
            dependencies=[Depends(RateLimiter(times=2, seconds=5))])
async def signup(body: UserModel, bt:BackgroundTasks, request:Request, db: Session = Depends(get_db)):
    exist_user = await repository_users.get_user_by_mail(body.mail, db)
    if exist_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT , detail="Account allready exist")
    body.password = auth_service.get_password_hash(body.password)
    new_user = await repository_users.create_user(body, db)
    bt.add_task(send_email, new_user.mail, new_user.username, str(request.base_url))
    return new_user


@router.post("/login", response_model = TokenModel,  dependencies=[Depends(RateLimiter(times=2, seconds=5))])
async def login(body: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = await repository_users.get_user_by_mail(body.username , db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    if not user.confirmed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email verifi")
    if not auth_service.verify_password(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid pass")
    # Generate JWT
    access_token = await auth_service.create_access_token(data={"sub": user.mail, "some text":"some text!"})
    refresh_token = await auth_service.create_refresh_token(data={"sub": user.mail})
    await repository_users.update_token(user, refresh_token, db)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.get('/refresh_token', response_model = TokenModel)
async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(get_refresh_token), db: Session = Depends(get_db)):
    token = credentials.credentials
    mail = await auth_service.decode_refresh_token(token)
    user = await repository_users.get_user_by_mail(mail, db)
    if user.refresh_token != token:
        await repository_users.update_token(user, None, db)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token = await auth_service.create_access_token(data={"sub": mail})
    refresh_token = await auth_service.create_refresh_token(data={"sub": mail})
    await repository_users.update_token(user, refresh_token, db)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.get('/confirmed_email/{token}')
async def confirmed_email(token: str, db: Session = Depends(get_db)):
    email = await auth_service.get_email_from_token(token)
    user = await repository_users.get_user_by_mail(email, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error")
    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    await repository_users.confirmed_email(email, db)
    return {"message": "Email confirmed"}


@router.post('/request_email',  dependencies=[Depends(RateLimiter(times=1, seconds=5))])
async def request_email(body: RequestEmail, background_tasks: BackgroundTasks, request: Request,
                        db: Session = Depends(get_db)):
    user = await repository_users.get_user_by_mail(body.mail, db)

    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    if user:
        background_tasks.add_task(send_email, user.mail, user.username, str(request.base_url))
    return {"message": "Check your email for confirmation."}


@router.get("/{username}")
async def request_email(username:str, response: Response,  db: Session = Depends(get_db)):
    print(f"{username} user open email -> save tu db ")
    return FileResponse("static/1x1.png", media_type="image/png", content_disposition_type="inline")


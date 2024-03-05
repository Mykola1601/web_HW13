
import uvicorn
import pathlib
from pathlib import Path
from sqlalchemy import text
from typing import Callable
import redis.asyncio as redis
from ipaddress import ip_address
from fastapi_limiter import FastAPILimiter
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi import FastAPI, File, UploadFile, status, HTTPException, Depends, Request

from src.database.db import get_db
from src.conf.config import config
from src.routes import  contacts, auth, users
from middlewares import CustomHeaderMiddleware


MAX_FILE_SIZE = 1_000_000  # 1Mb

app = FastAPI()

origins = [ 
    "*",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],        # GET,POST...
    allow_headers=["*"]         )

BASE_DIR = Path(".")


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.add_middleware(CustomHeaderMiddleware)


app.include_router(users.router, prefix='/api')
app.include_router(auth.router, prefix='/api')
app.include_router(contacts.router, prefix='/api')


banned_ips = [ip_address("192.168.1.1"), ip_address("192.168.1.2") ]


@app.middleware("http")
async def ban_ips(request: Request, call_next: Callable):
    ip = ip_address(request.client.host)
    if ip in banned_ips:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "You are banned"})
    response = await call_next(request)
    return response


@app.on_event("startup")
async def startup():
    r = await redis.Redis(host=config.REDIS_DOMAIN, port=config.REDIS_PORT, db=0, encoding="utf-8", password=config.REDIS_PASS)
    await FastAPILimiter.init(r)
    

templates = Jinja2Templates(directory=BASE_DIR / "src" / "templates")

@app.get("/", response_class=HTMLResponse )
def index(request:Request):
    return templates.TemplateResponse("index.html", {"request":request, "our":"Build group python"})


@app.get("/api/healthchecker")
async def healthchecker(db: AsyncSession = Depends(get_db)):
    try:
        # Make request
        result = await db.execute(text("SELECT 1"))
        result = result.fetchone()
        if result is None:
            raise HTTPException(status_code=500, detail="Database is not configured correctly")
        return {"message": "Welcome to FastAPI!"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error connecting to the database")



@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File()):
    pathlib.Path("uploads").mkdir(exist_ok=True)
    file_path = f"uploads/{file.filename}"
    file_size = 0
    with open(file_path, "wb") as f:
        while True:
            chunk = await file.read(1024)
            if not chunk:
                break
            file_size += len(chunk)
            if file_size > MAX_FILE_SIZE:
                f.close()
                pathlib.Path(file_path).unlink()
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File to big")
            f.write(chunk)
    return {"file_path": file_path}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)


# docker-compose up
# uvicorn main:app --host localhost --port 8000 --reload

    
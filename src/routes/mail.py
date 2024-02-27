from pathlib import Path

from fastapi import APIRouter

from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import EmailStr, BaseModel
from typing import List

from src.conf.config import conf


router = APIRouter(prefix='/mails', tags=["mails"])

class EmailSchema(BaseModel):
    email: EmailStr


@router.post("/send-email")
async def send_in_background(background_tasks: BackgroundTasks, body: EmailSchema):
    message = MessageSchema(
        subject="Fastapi mail module",
        recipients=[body.email],
        template_body={"fullname": "Billy Jones"},
        subtype=MessageType.html
    )

    fm = FastMail(conf)

    background_tasks.add_task(fm.send_message, message, template_name="example_email.html")

    return {"message": "email has been sent"}


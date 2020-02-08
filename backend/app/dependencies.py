import datetime
import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

import aiohttp
import wtforms
from fastapi import HTTPException
from minio import Minio
from motor import motor_asyncio
from starlette.templating import Jinja2Templates
from wtforms.csrf.session import SessionCSRF

minio_client = Minio(
    os.getenv("MINIO_HOST"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=(not os.getenv("DEBUG")),
)


DB_NAME = os.getenv("DB_NAME", "app")
db_uri = os.getenv("MONGODB_URI", False)
db = None

HERE = Path(__file__).parent

templates = Jinja2Templates(directory=str(HERE / "templates"))

mailgun_enpoint = os.getenv("MAILGUN_ENDPOINT")
mailgun_key = os.getenv("MAILGUN_KEY")

if db_uri:
    db_client = motor_asyncio.AsyncIOMotorClient(db_uri)
    db = db_client.get_database()
else:
    db_uri = "mongodb://{username}:{password}@{host}:{port}".format(
        username=quote_plus(os.getenv("DB_USERNAME", "root")),
        password=quote_plus(os.getenv("DB_PASSWORD", "root")),
        host=quote_plus(os.getenv("DB_HOST", "localhost")),
        port=quote_plus(os.getenv("DB_PORT", "27017")),
    )
    db_client = motor_asyncio.AsyncIOMotorClient(db_uri)
    db: motor_asyncio.AsyncIOMotorDatabase = db_client[DB_NAME]


async def send_email(
    to: str,
    subject: str,
    text: str,
    from_address: str,
    from_name: str,
    reply_to: Optional[str] = None,
    high_priority: bool = False,
):
    message_data = {
        "from": f"{from_name} <{from_address}>",
        "to": to,
        "subject": subject,
        "text": text,
    }
    if reply_to:
        message_data["h:Reply-To"] = reply_to
    if high_priority:
        message_data["h:X-Priority"] = 1
        message_data["h:X-MSMail-Priority"] = "High"
        message_data["h:Importance"] = "High"
    async with aiohttp.ClientSession() as session:
        res = await session.post(
            mailgun_enpoint,
            auth=aiohttp.BasicAuth("api", mailgun_key),
            data=message_data,
        )
        if res.status != 200:
            raise HTTPException(status_code=500, detail="Could not send email.")


class CSRFForm(wtforms.Form):
    class Meta:
        csrf = True
        csrf_class = SessionCSRF
        csrf_secret = os.getenv("SECRET_KEY").encode("utf-8")
        csrf_time_limit = datetime.timedelta(minutes=20)

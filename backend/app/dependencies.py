import datetime
import os
from pathlib import Path
from urllib.parse import quote_plus

import wtforms
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


class CSRFForm(wtforms.Form):
    class Meta:
        csrf = True
        csrf_class = SessionCSRF
        csrf_secret = os.getenv("SECRET_KEY").encode("utf-8")
        csrf_time_limit = datetime.timedelta(minutes=20)


def comma_truncate_list(items: list, limit: int = 3):
    if not items:
        return ""
    show_items = items[:limit] if limit > 0 else items
    suffix = "..." if len(show_items) < len(items) else ""
    return ", ".join(show_items) + suffix


def comma_list(items: list):
    if not items:
        return ""
    return ", ".join(items)


templates.env.filters["comma_truncate_list"] = comma_truncate_list
templates.env.filters["comma_list"] = comma_list

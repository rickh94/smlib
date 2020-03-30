import logging
import os
import urllib.parse

import minio
import pymongo
from fastapi import FastAPI, Depends, HTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from starlette.status import HTTP_401_UNAUTHORIZED

from app.auth.models import UserInDB
from app.auth.router import auth_router
from app.auth.security import get_current_active_user
from app.dependencies import db, HERE, templates, minio_client
from app.composers.router import composer_router
from app.sheets.router import sheet_router
from app.tags.router import tag_router
from app.instruments.router import instrument_router

app = FastAPI(title="Sheet Music Database", version="20.02.0")

app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")

logger = logging.getLogger()

if os.getenv("DEBUG"):
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.CRITICAL)


@app.on_event("startup")
async def setup_db():
    await db.users.create_index("email", unique=True)
    await db.sheets.create_index("owner_email")
    await db.sheets.create_index("sheet_id", unique=True)
    await db.sheets.create_index(
        [
            ("piece", pymongo.TEXT),
            ("instruments", pymongo.TEXT),
            ("composers", pymongo.TEXT),
            ("tags", pymongo.TEXT),
            ("catalog_number", pymongo.TEXT),
        ],
        default_language="english",
    )
    await db.sheets.create_index("instruments")
    await db.sheets.create_index("composers")
    await db.sheets.create_index("tags")


@app.on_event("startup")
def ensure_bucket():
    try:
        if not minio_client.bucket_exists(os.getenv("MINIO_BUCKET_NAME")):
            minio_client.make_bucket(os.getenv("MINIO_BUCKET_NAME"))
    except minio.ResponseError:
        minio_client.make_bucket(os.getenv("MINIO_BUCKET_NAME"))


@app.get("/")
async def index(
    request: Request, _current_user: UserInDB = Depends(get_current_active_user)
):
    return templates.TemplateResponse("index.html", {"request": request})


app.include_router(
    auth_router,
    prefix="/auth",
    tags=["auth"],
    responses={401: {"description": "Authentication Failure"}},
)

app.include_router(sheet_router, prefix="/sheets")
app.include_router(composer_router, prefix="/composers")
app.include_router(tag_router, prefix="/tags")
app.include_router(instrument_router, prefix="/instruments")


@app.middleware("http")
async def redirect_unauthorized(request: Request, call_next):
    logger.debug("entering unauthorized middleware")
    response = await call_next(request)
    if response.status_code == HTTP_401_UNAUTHORIZED:
        next_location = urllib.parse.quote_plus(request.url.path)
        error = urllib.parse.quote_plus("Please Log In to access that page.")
        url = f"/auth/login?error={error}&next={next_location}"
        return RedirectResponse(url=url)
    return response


app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))

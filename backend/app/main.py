import logging
import os
import urllib.parse

from fastapi import FastAPI, Depends, HTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from starlette.status import HTTP_401_UNAUTHORIZED

from app.auth.models import UserInDB
from app.auth.router import auth_router
from app.auth.security import get_current_active_user
from app.dependencies import db, HERE, templates
from app.sheets.router import sheet_router

app = FastAPI(title="Sheet Music Database", version="20.02.0")

app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")

logger = logging.getLogger()


@app.on_event("startup")
async def setup_db():
    await db.users.create_index("email", unique=True)
    await db.sheets.create_index("owner_email")
    await db.sheets.create_index("instruments")
    await db.sheets.create_index("composers")


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

app.include_router(
    sheet_router, prefix="/sheets",
)


@app.middleware("http")
async def redirect_unauthorized(request: Request, call_next):
    logger.debug("entering unauthorized middleware")
    response = await call_next(request)
    if response.status_code == HTTP_401_UNAUTHORIZED:
        logger.debug(type(request.url.path))
        next_location = urllib.parse.quote_plus(request.url.path)
        error = urllib.parse.quote_plus("Please Log In to access that page.")
        url = f"/auth/login?error={error}&next={next_location}"
        return RedirectResponse(url=url)
    return response


app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))

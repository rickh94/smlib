import os
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from app.auth.router import auth_router
from app.dependencies import db, HERE

app = FastAPI(title="Sheet Music Database", version="20.02.0")

app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")


@app.on_event("startup")
async def setup_db():
    await db.users.create_index("email", unique=True)


app.include_router(
    auth_router,
    prefix="/auth",
    tags=["auth"],
    responses={401: {"description": "Authentication Failure"}},
)

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))

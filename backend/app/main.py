import os
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.auth.router import auth_router
from app.dependencies import db

app = FastAPI(title="Sheet Music Database", version="20.02.0")


@app.on_event("startup")
async def setup_db():
    await db.users.create_index("email", unique=True)


app.include_router(
    auth_router,
    prefix="/auth",
    tags=["auth"],
    responses={401: {"description": "Authentication Failure"}},
)

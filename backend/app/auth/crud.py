import logging
from typing import Optional

import bson
from motor import motor_asyncio

from app.auth import models
from app.dependencies import db

logger = logging.getLogger()


async def get_user_by_email(email: str) -> Optional[models.UserInDB]:
    user = await db.users.find_one({"email": email})
    if not user:
        return None
    return models.UserInDB.parse_obj(user)


async def create_user(user: models.UserInDB) -> models.UserInDB:
    result = await db.users.insert_one(
        user.dict(exclude={"password", "_id"}, skip_defaults=True)
    )
    created = await db.users.find_one({"_id": result.inserted_id})
    return models.UserInDB.parse_obj(created)


async def get_user_by_id(user_id: str) -> models.UserInDB:
    return await db.users.find_one({"_id": bson.ObjectId(user_id)})


async def get_all_users() -> motor_asyncio.AsyncIOMotorCursor:
    return db.users.find({})


async def update_user_by_email(
    email: str, updated: models.UserWithRole
) -> models.UserInDB:
    current = await db.users.find_one({"email": email})
    _id = current["_id"]
    await db.users.replace_one({"_id": _id}, updated.dict(exclude={"password", "_id"}))
    return await db.users.find_one({"_id": _id})


async def delete_user_by_email(email: str):
    return await db.users.delete_one({"email": email})

import os
import uuid
from typing import List

import pymongo
from motor import motor_asyncio

from app.dependencies import db
from app.sheets import models


async def create_sheet(sheet: models.Sheet) -> models.SheetInDB:
    sheet = models.SheetInDB.parse_obj(sheet)
    sheet.clean_empty_strings()
    sheet.clean_tags()
    result = await db.sheets.insert_one(sheet.dict())
    created = await db.sheets.find_one({"_id": result.inserted_id})
    return models.SheetInDB.parse_obj(created)


async def get_sheet_by_id(owner_email: str, sheet_id: uuid.UUID) -> models.SheetInDB:
    found = await db.sheets.find_one({"owner_email": owner_email, "sheet_id": sheet_id})
    return models.SheetInDB.parse_obj(found)


async def get_user_sheets(
    owner_email: str,
    page: int = 1,
    sort: str = "piece",
    direction: int = 1,
    limit: int = 20,
) -> motor_asyncio.AsyncIOMotorCursor:
    skip = limit * (page - 1)
    return db.sheets.find(
        {"owner_email": owner_email}, sort=[(sort, direction)], limit=limit, skip=skip,
    )


async def user_sheets_has_next(owner_email: str, page: int = 1, limit: int = 20):
    skip = limit * page
    count = await db.sheets.count_documents(
        {"owner_email": owner_email}, limit=1, skip=skip
    )
    return count > 0


async def piece_related_has_next(sheet: models.Sheet, page: int = 1, limit: int = 20):
    skip = limit * page
    count = await db.sheets.count_documents(
        {
            "owner_email": sheet.owner_email,
            "piece": sheet.piece,
            "sheet_id": {"$ne": sheet.sheet_id},
        },
        limit=1,
        skip=skip,
    )
    return count > 0


async def get_piece_related(
    sheet: models.Sheet,
    limit: int = 3,
    page: int = 1,
    sort: str = "piece",
    direction: int = 1,
) -> List[models.SheetOut]:
    skip = limit * (page - 1)
    cursor = db.sheets.find(
        {
            "owner_email": sheet.owner_email,
            "piece": sheet.piece,
            "sheet_id": {"$ne": sheet.sheet_id},
        },
        limit=limit,
        skip=skip,
        sort=[(sort, direction)],
    )
    return [models.SheetOut.parse_obj(sheet) async for sheet in cursor]

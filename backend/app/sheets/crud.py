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


async def related_has_next(
    sheet: models.Sheet,
    field: str,
    page: int = 1,
    limit: int = 20,
    exclude: bool = True,
):
    skip = limit * page
    count = await db.sheets.count_documents(
        generate_related_query(sheet, field, exclude), limit=1, skip=skip,
    )
    return count > 0


def generate_related_query(sheet, field, exclude):
    query_filter = {
        field: getattr(sheet, field),
        "owner_email": sheet.owner_email,
    }
    if isinstance(query_filter[field], list):
        query_filter[field] = {"$elemMatch": {"$in": query_filter[field]}}
    if exclude:
        query_filter["sheet_id"] = {"$ne": sheet.sheet_id}
    return query_filter


async def find_related(
    sheet: models.Sheet,
    field: str,
    limit: int = 3,
    page: int = 1,
    sort: str = "piece",
    direction: int = 1,
    exclude: bool = True,
):
    skip = limit * (page - 1)
    query_filter = generate_related_query(sheet, field, exclude)
    cursor = db.sheets.find(
        query_filter, limit=limit, skip=skip, sort=[(sort, direction)],
    )
    return [models.SheetOut.parse_obj(sheet) async for sheet in cursor]


async def get_piece_related(
    sheet: models.Sheet,
    limit: int = 3,
    page: int = 1,
    sort: str = "piece",
    direction: int = 1,
) -> List[models.SheetOut]:
    return await find_related(sheet, "piece", limit, page, sort, direction)

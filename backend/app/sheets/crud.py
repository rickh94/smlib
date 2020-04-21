import datetime
import uuid
from typing import List

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


class DuplicateID(Exception):
    pass


async def update_sheet(
    old_sheet: models.SheetWithVersions, new_sheet: models.Sheet
) -> models.SheetInDB:
    if new_sheet.sheet_id == old_sheet.sheet_id:
        raise DuplicateID()
    new_sheet = models.SheetInDB.parse_obj(new_sheet)
    old_sheet.current = False
    old_sheet.clean_empty_strings()
    old_sheet.clean_tags()
    await db.sheets.find_one_and_replace(
        {"sheet_id": old_sheet.sheet_id}, old_sheet.dict()
    )
    new_sheet.prev_versions = []
    new_sheet.prev_versions.append((old_sheet.sheet_id, datetime.datetime.now()))
    if old_sheet.prev_versions:
        new_sheet.prev_versions.extend(old_sheet.prev_versions)
    new_sheet.clean_empty_strings()
    new_sheet.clean_tags()
    result = await db.sheets.insert_one(new_sheet.dict())
    created = await db.sheets.find_one({"_id": result.inserted_id})
    return models.SheetInDB.parse_obj(created)


async def restore_previous_sheet(
    sheet_to_restore: models.SheetInDB, current_version_sheet: models.SheetInDB
) -> models.SheetInDB:
    sheet_to_restore.current = True
    versions = [(current_version_sheet.sheet_id, datetime.datetime.now())]
    versions.extend(
        [
            item
            for item in current_version_sheet.prev_versions
            if item[1] == sheet_to_restore.sheet_id
        ]
    )
    sheet_to_restore.prev_versions = versions
    await db.sheets.find_one_and_update(
        {"sheet_id": current_version_sheet.sheet_id}, {"$set": {"current": False}}
    )
    result = await db.sheets.find_one_and_replace(
        {
            "sheet_id": sheet_to_restore.sheet_id,
            "owner_email": sheet_to_restore.owner_email,
        },
        sheet_to_restore.dict(),
    )
    return models.SheetInDB.parse_obj(result)


async def get_sheet_by_id(owner_email: str, sheet_id: uuid.UUID) -> models.SheetInDB:
    found = await db.sheets.find_one({"owner_email": owner_email, "sheet_id": sheet_id})
    return models.SheetInDB.parse_obj(found)


async def get_previous_versions(sheet: models.SheetInDB):
    if sheet.prev_versions:
        return [
            (await get_sheet_by_id(sheet.owner_email, version_id), replacement_time)
            for (version_id, replacement_time) in sheet.prev_versions
        ]
    return []


async def get_user_sheets(
    owner_email: str,
    page: int = 1,
    sort: str = "piece",
    direction: int = 1,
    limit: int = 20,
) -> motor_asyncio.AsyncIOMotorCursor:
    skip = limit * (page - 1)
    return db.sheets.find(
        {"owner_email": owner_email, "current": True},
        sort=[(sort, direction)],
        limit=limit,
        skip=skip,
    )


async def user_sheets_has_next(owner_email: str, page: int = 1, limit: int = 20):
    skip = limit * page
    count = await db.sheets.count_documents(
        {"owner_email": owner_email, "current": True}, limit=1, skip=skip
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
        generate_related_query(sheet, field, exclude), limit=1, skip=skip
    )
    return count > 0


def generate_related_query(sheet, field, exclude):
    query_filter = {
        field: getattr(sheet, field),
        "owner_email": sheet.owner_email,
        "current": True,
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
        query_filter, limit=limit, skip=skip, sort=[(sort, direction)]
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


async def delete_sheet_by_id(owner_email: str, sheet_id: uuid.UUID):
    sheet = models.SheetInDB.parse_obj(await get_sheet_by_id(owner_email, sheet_id))
    if sheet.prev_versions:
        for version_id, _ in sheet.prev_versions:
            await db.sheets.delete_one(
                {"owner_email": owner_email, "sheet_id": version_id}
            )
    await db.sheets.delete_one({"owner_email": owner_email, "sheet_id": sheet_id})


def find_sheet_from_text(
    owner_email: str,
    search_terms: str,
    page: int = 1,
    sort: str = "piece",
    direction: int = 1,
    limit: int = 20,
):
    skip = limit * (page - 1)
    return db.sheets.find(
        {
            "owner_email": owner_email,
            "current": True,
            "$text": {"$search": search_terms},
        },
        sort=[(sort, direction)],
        limit=limit,
        skip=skip,
    )


async def sheet_search_has_next(owner_email, search_text, page, limit):
    skip = limit * page
    count = await db.sheets.count_documents(
        {
            "owner_email": owner_email,
            "current": True,
            "$text": {"$search": search_text},
        },
        limit=limit,
        skip=skip,
    )
    return count > 0

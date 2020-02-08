import uuid

from app.dependencies import db
from app.sheets import models


async def create_sheet(sheet: models.Sheet) -> models.SheetInDB:
    sheet = models.SheetInDB.parse_obj(sheet)
    sheet.clean_empty_strings()
    result = await db.sheets.insert_one(sheet.dict())
    created = await db.sheets.find_one({"_id": result.inserted_id})
    return models.SheetInDB.parse_obj(created)


async def get_sheet_by_id(owner_email: str, sheet_id: uuid.UUID) -> models.SheetInDB:
    found = await db.sheets.find_one({"owner_email": owner_email, "sheet_id": sheet_id})
    return models.SheetInDB.parse_obj(found)

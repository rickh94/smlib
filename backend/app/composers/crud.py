from app.dependencies import db
from app.sheets.models import SheetOut


def get_composer_query(owner_email, composer_name):
    return {
        "owner_email": owner_email,
        "composers": {"$elemMatch": {"$eq": composer_name}},
    }


async def get_all_composers(email: str):
    return await db.sheets.distinct("composers", {"owner_email": email})


async def get_composer_sheets(
    owner_email: str,
    composer_name: str,
    limit: int = 20,
    page: int = 1,
    sort: str = "piece",
    direction: int = 1,
):
    skip = limit * (page - 1)
    cursor = db.sheets.find(
        get_composer_query(owner_email, composer_name),
        limit=limit,
        skip=skip,
        sort=[(sort, direction)],
    )
    return [SheetOut.parse_obj(sheet) async for sheet in cursor]


async def composer_sheets_has_next(
    owner_email: str, composer_name: str, limit: int = 20, page: int = 1
):
    skip = limit * page
    count = await db.sheets.count_documents(
        get_composer_query(owner_email, composer_name), limit=1, skip=skip
    )
    return count > 0

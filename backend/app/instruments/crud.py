from app.dependencies import db
from app.sheets.models import SheetOut


def get_instrument_query(owner_email, instrument_name):
    return {
        "owner_email": owner_email,
        "instruments": {"$elemMatch": {"$eq": instrument_name}},
        "current": True,
    }


async def get_all_instruments(email: str):
    return await db.sheets.distinct(
        "instruments", {"owner_email": email, "current": True}
    )


async def get_instrument_sheets(
    owner_email: str,
    instrument_name: str,
    limit: int = 20,
    page: int = 1,
    sort: str = "piece",
    direction: int = 1,
):
    skip = limit * (page - 1)
    cursor = db.sheets.find(
        get_instrument_query(owner_email, instrument_name),
        limit=limit,
        skip=skip,
        sort=[(sort, direction)],
    )
    return [SheetOut.parse_obj(sheet) async for sheet in cursor]


async def instrument_sheets_has_next(
    owner_email: str, instrument_name: str, limit: int = 20, page: int = 1
):
    skip = limit * page
    count = await db.sheets.count_documents(
        get_instrument_query(owner_email, instrument_name), limit=1, skip=skip
    )
    return count > 0

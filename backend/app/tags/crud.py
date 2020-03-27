from app.dependencies import db
from app.sheets.models import SheetOut


def get_tag_query(owner_email, tag_name):
    return {
        "owner_email": owner_email,
        "tags": {"$elemMatch": {"$eq": tag_name}},
        "current": True,
    }


async def get_all_tags(email: str):
    return await db.sheets.distinct(
        "tags", {"owner_email": email, "current": True}
    )


async def get_tag_sheets(
    owner_email: str,
    tag_name: str,
    limit: int = 20,
    page: int = 1,
    sort: str = "piece",
    direction: int = 1,
):
    skip = limit * (page - 1)
    cursor = db.sheets.find(
        get_tag_query(owner_email, tag_name),
        limit=limit,
        skip=skip,
        sort=[(sort, direction)],
    )
    return [SheetOut.parse_obj(sheet) async for sheet in cursor]


async def tag_sheets_has_next(
    owner_email: str, tag_name: str, limit: int = 20, page: int = 1
):
    skip = limit * page
    count = await db.sheets.count_documents(
        get_tag_query(owner_email, tag_name), limit=1, skip=skip
    )
    return count > 0

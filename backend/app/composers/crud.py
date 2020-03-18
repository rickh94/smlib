from app.dependencies import db


async def get_all_composers(email: str):
    return await db.sheets.distinct("composers", {"owner_email": email})

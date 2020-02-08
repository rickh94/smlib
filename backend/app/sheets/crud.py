from fastapi import File, UploadFile

from app.dependencies import db
from app.sheets import models


# async def save_sheet(sheet: models.Sheet, sheet_file: UploadFile):
#     file_ext = sheet_file.filename.spit('.')[-1]
#     file_name =
#     # sheet = models.SheetInDB(**sheet.dict(), path=)

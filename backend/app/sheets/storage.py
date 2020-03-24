import os
import tempfile
from uuid import UUID

from fastapi import UploadFile

from app.dependencies import minio_client


async def save_sheet(
    sheet_file: UploadFile, sheet_id: UUID, owner_email: str, sheet_file_ext: str
):
    tmp_sheet = tempfile.NamedTemporaryFile()
    tmp_sheet.write(await sheet_file.read())
    tmp_sheet.seek(0)
    sheet_stats = os.stat(tmp_sheet.name)
    result = minio_client.put_object(
        os.getenv("MINIO_BUCKET_NAME"),
        f"{owner_email}/{sheet_id}.{sheet_file_ext}",
        tmp_sheet,
        sheet_stats.st_size,
    )
    print(result)
    tmp_sheet.close()


def get_sheet(sheet_id: UUID, owner_email: str, sheet_file_ext: str):
    return minio_client.get_object(
        os.getenv("MINIO_BUCKET_NAME"), f"{owner_email}/{sheet_id}.{sheet_file_ext}"
    )


def copy_sheet(
    old_sheet_id: UUID, new_sheet_id: UUID, owner_email: str, sheet_file_ext: str
):
    minio_client.copy_object(
        os.getenv("MINIO_BUCKET_NAME"),
        f"{owner_email}/{new_sheet_id}.{sheet_file_ext}",
        f"/{os.getenv('MINIO_BUCKET_NAME')}/{owner_email}/{old_sheet_id}.{sheet_file_ext}",
    )

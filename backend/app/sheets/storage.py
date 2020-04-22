import logging
import os
import tempfile
from uuid import UUID

import minio
from fastapi import UploadFile
from pdf2image import convert_from_bytes

from app.dependencies import minio_client

logger = logging.getLogger()


async def save_sheet(
    sheet_file: UploadFile, sheet_id: UUID, owner_email: str, sheet_file_ext: str
):
    tmp_sheet = tempfile.NamedTemporaryFile()
    tmp_sheet.write(await sheet_file.read())
    tmp_sheet.seek(0)
    sheet_stats = os.stat(tmp_sheet.name)
    # logger.debug(f"Sheet id for upload: {sheet_id}")
    result = minio_client.put_object(
        os.getenv("MINIO_BUCKET_NAME"),
        f"{owner_email}/{sheet_id}.{sheet_file_ext}",
        tmp_sheet,
        sheet_stats.st_size,
    )
    logger.debug(result)
    if sheet_file_ext.lower() == "pdf":
        tmp_sheet.seek(0)
        images = convert_from_bytes(
            tmp_sheet.read(),
            dpi=50,
            use_cropbox=True,
            first_page=1,
            last_page=1,
            grayscale=True,
        )
        tmp_preview = tempfile.NamedTemporaryFile()
        images[0].save(tmp_preview, format="PNG")
        tmp_preview.seek(0)
        preview_stats = os.stat(tmp_preview.name)
        preview_result = minio_client.put_object(
            os.getenv("MINIO_BUCKET_NAME"),
            f"{owner_email}/{sheet_id}-preview.png",
            tmp_preview,
            preview_stats.st_size,
        )
        logger.debug(preview_result)
        tmp_preview.close()
    tmp_sheet.close()


def get_sheet(sheet_id: UUID, owner_email: str, sheet_file_ext: str):
    return minio_client.get_object(
        os.getenv("MINIO_BUCKET_NAME"), f"{owner_email}/{sheet_id}.{sheet_file_ext}"
    )


def get_preview(sheet_id: UUID, owner_email: str):
    return minio_client.get_object(
        os.getenv("MINIO_BUCKET_NAME"), f"{owner_email}/{sheet_id}-preview.png"
    )


def copy_sheet(
    old_sheet_id: UUID, new_sheet_id: UUID, owner_email: str, sheet_file_ext: str
):
    minio_client.copy_object(
        os.getenv("MINIO_BUCKET_NAME"),
        f"{owner_email}/{new_sheet_id}.{sheet_file_ext}",
        f"/{os.getenv('MINIO_BUCKET_NAME')}/{owner_email}/{old_sheet_id}.{sheet_file_ext}",
    )

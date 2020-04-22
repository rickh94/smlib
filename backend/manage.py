import os
import tempfile
from pathlib import Path
from urllib.parse import quote_plus

import click
import pymongo
from pdf2image import convert_from_bytes

from app.auth.models import UserInDB, AuthRole
from app.dependencies import minio_client
from app.sheets import models

db_uri = "mongodb://{username}:{password}@{host}:{port}".format(
    username=quote_plus(os.getenv("DB_USERNAME", "root")),
    password=quote_plus(os.getenv("DB_PASSWORD", "root")),
    host=quote_plus(os.getenv("DB_HOST", "localhost")),
    port=quote_plus(os.getenv("DB_PORT", "27017")),
)
db_client = pymongo.MongoClient(db_uri)
db = db_client[os.getenv("DB_NAME", "app")]

# test volume
@click.group()
def cli():
    pass


@cli.command()
@click.option("-e", "--email", prompt=True, type=str)
def createsuperuser(email):
    # email = click.prompt("Email", type=str)
    admin = UserInDB(email=email, role=AuthRole.admin)
    result = db.users.insert_one(admin.dict())
    if result.inserted_id:
        print("User creation successful")
    else:
        print("user creation failed")


@cli.command()
def createdata():
    if "testdata" not in os.listdir("/"):
        print("No data to add")
        raise SystemExit(1)
    folders = os.listdir("/testdata")
    for folder in folders:
        data_path = Path("/") / "testdata" / folder / "data.json"
        sheet_path = Path("/") / "testdata" / folder / "sheet.pdf"
        sheet = models.SheetInDB.parse_file(data_path)
        if db.sheets.find_one({"sheet_id": sheet.sheet_id}):
            print(f"skipping {sheet.piece} id: {sheet.sheet_id}")
            continue
        sheet.clean_empty_strings()
        sheet.clean_tags()
        db.sheets.insert_one(sheet.dict())
        sheet_stats = os.stat(str(sheet_path.absolute()))
        sheet_file = sheet_path.open("rb")
        minio_client.put_object(
            os.getenv("MINIO_BUCKET_NAME"),
            f"{sheet.owner_email}/{sheet.sheet_id}.{sheet.file_ext}",
            sheet_file,
            sheet_stats.st_size,
        )
        sheet_file.seek(0)
        images = convert_from_bytes(
            sheet_file.read(),
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
        minio_client.put_object(
            os.getenv("MINIO_BUCKET_NAME"),
            f"{sheet.owner_email}/{sheet.sheet_id}-preview.png",
            tmp_preview,
            preview_stats.st_size,
        )
        tmp_preview.close()
        sheet_file.close()


if __name__ == "__main__":
    cli()

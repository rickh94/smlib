import os
from urllib.parse import quote_plus

import click
import pymongo

from app.auth.models import UserInDB, AuthRole

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
def createsuperuser():
    email = click.prompt("Email", type=str)
    admin = UserInDB(email=email, role=AuthRole.admin)
    result = db.users.insert_one(admin.dict())
    if result.inserted_id:
        print("User creation successful")
    else:
        print("user creation failed")


if __name__ == "__main__":
    cli()

import os
import uuid
from urllib.parse import quote_plus

import pymongo
import pytest
from motor import motor_asyncio

from starlette.testclient import TestClient

from app.main import app


@pytest.fixture
def db_name():
    return str(uuid.uuid4())


@pytest.fixture
def db(db_name):
    db_uri = "mongodb://{username}:{password}@{host}:{port}".format(
        username=quote_plus(os.getenv("DB_USERNAME", "root")),
        password=quote_plus(os.getenv("DB_PASSWORD", "root")),
        host=quote_plus(os.getenv("DB_HOST", "localhost")),
        port=quote_plus(os.getenv("DB_PORT", "27017")),
    )
    db_client = pymongo.MongoClient(db_uri)
    return db_client[db_name]


@pytest.fixture
def async_db(db_name):
    db_uri = "mongodb://{username}:{password}@{host}:{port}".format(
        username=quote_plus(os.getenv("DB_USERNAME", "root")),
        password=quote_plus(os.getenv("DB_PASSWORD", "root")),
        host=quote_plus(os.getenv("DB_HOST", "localhost")),
        port=quote_plus(os.getenv("DB_PORT", "27017")),
    )
    db_client = motor_asyncio.AsyncIOMotorClient(db_uri)
    return db_client[db_name]


@pytest.fixture
def test_client():
    return TestClient(app)

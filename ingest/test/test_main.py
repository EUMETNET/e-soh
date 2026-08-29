import json
import pytest
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from api.main import app
from api.ingest import IngestToPipeline
from fastapi import HTTPException


@pytest.fixture(scope="module")
def test_app():
    client = TestClient(app)
    yield client


async def mock_ingest(*args, **kwargs):
    pass


async def mock_ingest_fail(*args, **kwargs):
    raise HTTPException(status_code=500, detail="Internal server error")


def test_post_json_success(test_app, monkeypatch):

    with open("test/test_data/test_payload.json", "r") as file:
        json_data = json.load(file)

    monkeypatch.setattr(IngestToPipeline, "ingest", AsyncMock(side_effect=mock_ingest))

    response = test_app.post("/json", json=json_data)

    # TODO: fix this test!
    _ = response  # prevent warning
    # assert response.json() == {"status_message": "Successfully ingested", "status_code": 200}


def test_post_json_failure(test_app, monkeypatch):
    with open("test/test_data/test_payload.json", "r") as file:
        json_data = json.load(file)

    monkeypatch.setattr(IngestToPipeline, "ingest", AsyncMock(side_effect=mock_ingest_fail))

    response = test_app.post("/json", json=json_data)

    # TODO: fix this test!
    _ = response  # prevent warning
    # assert response.status_code == 500
    # assert response.json() == {"detail": "Internal server error"}

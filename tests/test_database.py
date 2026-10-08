
import sqlite3
from decimal import Decimal

import pytest

import database


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Create a temporary database for each test."""

    db_path = tmp_path / "test_breakage.db"

    monkeypatch.setattr(database, "DATABASE_PATH", db_path)

    database.initialize_database()

    return db_path


def make_record(cost, status="READY"):
    """Create a sample CCD record."""

    return {
        "item_id": "TEST-ITEM-001",
        "job_id": "TEST-JOB-001",
        "job_name": "Test Job",
        "description": "Damaged Vacuum",
        "room": "Living Room",
        "quantity": 1,
        "cost_type": "REPLACEMENT" if status == "READY" else None,
        "cost": Decimal(str(cost)) if cost is not None else None,
        "status": status,
    }


def get_events(db_path):
    """Retrieve financial events from the test database."""

    with sqlite3.connect(db_path) as connection:
        return connection.execute(
            "SELECT event_type, amount FROM financial_events"
        ).fetchall()


def test_new_damage(test_db):
    result = database.save_damage_record(make_record(50))

    assert result == "NEW"
    assert get_events(test_db) == [("NEW_LOSS", "50")]


def test_duplicate_damage(test_db):
    database.save_damage_record(make_record(50))
    result = database.save_damage_record(make_record(50))

    assert result == "UNCHANGED"
    assert len(get_events(test_db)) == 1


def test_cost_adjustment(test_db):
    database.save_damage_record(make_record(50))
    result = database.save_damage_record(make_record(75))

    assert result == "ADJUSTED"

    assert get_events(test_db) == [
        ("NEW_LOSS", "50"),
        ("COST_ADJUSTMENT", "25"),
    ]


def test_pending_to_ready(test_db):
    database.save_damage_record(
        make_record(None, status="PENDING")
    )

    assert get_events(test_db) == []

    result = database.save_damage_record(make_record(100))

    assert result == "COST_ADDED"
    assert get_events(test_db) == [("NEW_LOSS", "100")]


def test_review_does_not_erase_cost(test_db):
    database.save_damage_record(make_record(50))

    result = database.save_damage_record(
        make_record(None, status="REVIEW")
    )

    assert result == "PENDING_REVIEW"
    assert get_events(test_db) == [("NEW_LOSS", "50")]

    with sqlite3.connect(test_db) as connection:
        saved = connection.execute(
            "SELECT current_cost, status FROM damaged_items"
        ).fetchone()

    assert saved == ("50", "REVIEW")

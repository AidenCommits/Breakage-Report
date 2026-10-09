from decimal import Decimal
import pytest

import database

@pytest.fixture
def test_db(tmp_path, monkeypatch):
    db_path = tmp_path / "historical_test.db"

    monkeypatch.setattr(database, "DATABASE_PATH", db_path)
    database.initialize_database()

    return db_path

def make_record(job_id, job_name, cost):
    return {
        "item_id": "TEST-ITEM-001",
        "job_id": job_id,
        "job_name": job_name,
        "description": "Damaged Vacuum",
        "room": "Living Room",
        "quantity": 1,
        "cost_type": "REPLACEMENT",
        "cost": Decimal(str(cost)),
        "status": "READY",
    }

def test_original_event_keeps_original_job(test_db):
    # First, record a $50 loss under Job A.
    original = make_record("JOB-A", "Original Job", 50)

    assert database.save_damage_record(original) == "NEW"

    # The item moves to Job B and its cost increases.
    updated = make_record("JOB-B", "New Job", 75)

    assert database.save_damage_record(updated) == "ADJUSTED"

    # Read the historical financial events.
    with database.get_connection() as connection:
        events = connection.execute(
            """
            SELECT
                event_type,
                amount,
                job_id,
                job_name
            FROM financial_events
            ORDER BY event_id
            """
        ).fetchall()

    assert len(events) == 2

    # Original loss remains assigned to Job A.
    assert events[0]["event_type"] == "NEW_LOSS"
    assert events[0]["amount"] == "50"
    assert events[0]["job_id"] == "JOB-A"
    assert events[0]["job_name"] == "Original Job"

    # Adjustment is assigned to Job B.
    assert events[1]["event_type"] == "COST_ADJUSTMENT"
    assert events[1]["amount"] == "25"
    assert events[1]["job_id"] == "JOB-B"
    assert events[1]["job_name"] == "New Job"

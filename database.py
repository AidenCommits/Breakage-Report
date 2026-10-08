
import sqlite3

from config import DATABASE_PATH
from datetime import datetime, timezone
from decimal import Decimal


def get_connection():
    """Open a connection to the SQLite database."""

    connection = sqlite3.connect(DATABASE_PATH)

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database():
    """Create database tables if they don't already exist."""

    with get_connection() as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS damaged_items (
                item_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                job_name TEXT,
                description TEXT,
                room TEXT,
                quantity REAL,
                cost_type TEXT,
                current_cost TEXT,
                status TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS financial_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                amount TEXT NOT NULL,
                recorded_at TEXT NOT NULL,

                FOREIGN KEY (item_id)
                    REFERENCES damaged_items(item_id)
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_damaged_items_status
            ON damaged_items(status)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_financial_events_date
            ON financial_events(recorded_at)
        """)

    print("Database initialized successfully.")


def save_damage_record(record):
    """Save a CCD item and record financial changes."""

    now = datetime.now(timezone.utc).isoformat()

    item_id = record["item_id"]
    new_status = record["status"]
    new_cost = record["cost"]

    if new_status == "READY" and new_cost is None:
        raise ValueError("READY items must have a cost.")

    with get_connection() as connection:

        existing = connection.execute(
            """
            SELECT *
            FROM damaged_items
            WHERE item_id = ?
            """,
            (item_id,)
        ).fetchone()

        if existing is None:
            # First time discovering this CCD item.
            connection.execute(
                """
                INSERT INTO damaged_items (
                    item_id, job_id, job_name,
                    description, room, quantity,
                    cost_type, current_cost, status,
                    first_seen, last_seen
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    record["job_id"],
                    record.get("job_name"),
                    record.get("description"),
                    record.get("room"),
                    record.get("quantity"),
                    record.get("cost_type") if new_status == "READY" else None,
                    str(new_cost) if new_status == "READY" else None,
                    new_status,
                    now,
                    now,
                )
            )

            if new_status == "READY":
                connection.execute(
                    """
                    INSERT INTO financial_events (
                        item_id, event_type, amount, recorded_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (item_id, "NEW_LOSS", str(new_cost), now)
                )

            return "NEW"

        # Item already exists in our database.
        old_cost = (
            Decimal(existing["current_cost"])
            if existing["current_cost"] is not None
            else None
        )

        # A pending/review result should not erase
        # a previously verified financial amount.
        if new_status != "READY":
            connection.execute(
                """
                UPDATE damaged_items
                SET job_id = ?, job_name = ?,
                    description = ?, room = ?,
                    quantity = ?, status = ?,
                    last_seen = ?
                WHERE item_id = ?
                """,
                (
                    record["job_id"],
                    record.get("job_name"),
                    record.get("description"),
                    record.get("room"),
                    record.get("quantity"),
                    new_status,
                    now,
                    item_id,
                )
            )

            return "PENDING_REVIEW"

        new_cost = Decimal(str(new_cost))

        connection.execute(
            """
            UPDATE damaged_items
            SET job_id = ?, job_name = ?,
                description = ?, room = ?,
                quantity = ?, cost_type = ?,
                current_cost = ?, status = ?,
                last_seen = ?
            WHERE item_id = ?
            """,
            (
                record["job_id"],
                record.get("job_name"),
                record.get("description"),
                record.get("room"),
                record.get("quantity"),
                record.get("cost_type"),
                str(new_cost),
                new_status,
                now,
                item_id,
            )
        )

        if old_cost is None:
            # Previously pending; cost now available.
            connection.execute(
                """
                INSERT INTO financial_events (
                    item_id, event_type, amount, recorded_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (item_id, "NEW_LOSS", str(new_cost), now)
            )

            return "COST_ADDED"

        if new_cost != old_cost:
            difference = new_cost - old_cost

            connection.execute(
                """
                INSERT INTO financial_events (
                    item_id, event_type, amount, recorded_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    item_id,
                    "COST_ADJUSTMENT",
                    str(difference),
                    now,
                )
            )

            return "ADJUSTED"

        return "UNCHANGED"

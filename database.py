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
                job_id TEXT,
                job_name TEXT,
                cost_type TEXT,
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
            connection.execute(
                """
                INSERT INTO damaged_items (
                    item_id,
                    job_id,
                    job_name,
                    description,
                    room,
                    quantity,
                    cost_type,
                    current_cost,
                    status,
                    first_seen,
                    last_seen
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["item_id"],
                    record["job_id"],
                    record.get("job_name"),
                    record.get("description"),
                    record.get("room"),
                    record.get("quantity"),
                    record.get("cost_type"),
                    str(new_cost) if new_cost is not None else None,
                    new_status,
                    now,
                    now,
                ),
            )

            if new_status == "READY":

                # NEW SECTION 1:
                # Store a snapshot of job and cost type
                # when the initial financial loss occurs.
                connection.execute(
                    """
                    INSERT INTO financial_events (
                        item_id,
                        event_type,
                        amount,
                        recorded_at,
                        job_id,
                        job_name,
                        cost_type
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["item_id"],
                        "NEW_LOSS",
                        str(new_cost),
                        now,
                        record["job_id"],
                        record.get("job_name"),
                        record.get("cost_type"),
                    ),
                )

            return "NEW"
        # ------------------------------------------
        # CASE 2: Existing damaged item
        # ------------------------------------------
        old_cost = (
            Decimal(existing["current_cost"])
            if existing["current_cost"] is not None
            else None
        )

        # Item is pending or needs review.
        # Preserve any previously recorded cost.
        if new_status != "READY":
            connection.execute(
                """
                UPDATE damaged_items
                SET
                    job_id = ?,
                    job_name = ?,
                    description = ?,
                    room = ?,
                    quantity = ?,
                    status = ?,
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
                    record["item_id"],
                ),
            )

            return "PENDING_REVIEW"

        # Update the item with its latest valid cost.
        connection.execute(
            """
            UPDATE damaged_items
            SET
                job_id = ?,
                job_name = ?,
                description = ?,
                room = ?,
                quantity = ?,
                cost_type = ?,
                current_cost = ?,
                status = ?,
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
                record["item_id"],
            ),
        )

        
        if old_cost is None:
            # Previously pending; cost now available.
            event_type = "NEW_LOSS"
            amount = new_cost
            result = "COST_ADDED"

        elif new_cost != old_cost:
            # Existing cost has changed.
            event_type = "COST_ADJUSTMENT"
            amount = new_cost - old_cost
            result = "ADJUSTED"

        else:
            # No financial changes.
            return "UNCHANGED"

        # Save the financial event with historical metadata.
        connection.execute(
            """
            INSERT INTO financial_events (
                item_id,
                event_type,
                amount,
                recorded_at,
                job_id,
                job_name,
                cost_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                event_type,
                str(amount),
                now,
                record["job_id"],
                record.get("job_name"),
                record.get("cost_type"),
            ),
        )

        return result


def migrate_financial_events():
    """Add historical metadata columns to existing databases."""

    columns_to_add = {
        "job_id": "TEXT",
        "job_name": "TEXT",
        "cost_type": "TEXT",
    }

    with get_connection() as connection:
        existing_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(financial_events)"
            ).fetchall()
        }

        for column, column_type in columns_to_add.items():
            if column not in existing_columns:
                connection.execute(
                    f"ALTER TABLE financial_events "
                    f"ADD COLUMN {column} {column_type}"
                )

        # Backfill existing events from their current item
        # metadata. This is an approximation for older events.
        connection.execute("""
            UPDATE financial_events
            SET
                job_id = (
                    SELECT job_id
                    FROM damaged_items
                    WHERE damaged_items.item_id =
                          financial_events.item_id
                ),
                job_name = (
                    SELECT job_name
                    FROM damaged_items
                    WHERE damaged_items.item_id =
                          financial_events.item_id
                ),
                cost_type = (
                    SELECT cost_type
                    FROM damaged_items
                    WHERE damaged_items.item_id =
                          financial_events.item_id
                )
            WHERE job_id IS NULL
        """)

    print("Financial event migration complete.")

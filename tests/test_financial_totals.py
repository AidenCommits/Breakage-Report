
from decimal import Decimal
from database import get_connection


def main():
    with get_connection() as connection:
        items = connection.execute(
            "SELECT COUNT(*) AS total FROM damaged_items"
        ).fetchone()

        events = connection.execute(
            """
            SELECT event_type, amount
            FROM financial_events
            ORDER BY event_id
            """
        ).fetchall()

    total = sum(
        (Decimal(event["amount"]) for event in events),
        Decimal("0"),
    )

    print(f"Damaged items stored: {items['total']}")
    print(f"Financial events stored: {len(events)}")
    print(f"Total recognized losses: ${total:.2f}")

    print("\nFinancial events:")
    for event in events:
        print(f"{event['event_type']}: ${Decimal(event['amount']):.2f}")


if __name__ == "__main__":
    main()

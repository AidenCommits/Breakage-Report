
from database import (
    initialize_database,
    get_connection,
)


def main():

    initialize_database()

    with get_connection() as connection:

        tables = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
        """).fetchall()

        print("\nDatabase tables:")

        for table in tables:
            print(table["name"])


if __name__ == "__main__":
    main()

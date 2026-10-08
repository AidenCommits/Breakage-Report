
from auth import ContentsTrackBrowser
from ct_api import ContentsTrackApi
from processor import scan_recent_jobs
from database import initialize_database, save_damage_record


def main():
    browser = ContentsTrackBrowser()

    try:
        print("Starting ContentsTrack...")
        browser.start()

        if not browser.wait_for_api_headers(timeout=30):
            raise RuntimeError(
                "Could not capture authenticated API headers."
            )

        session_data = browser.get_api_session_data()

        api = ContentsTrackApi(
            headers=session_data["headers"],
            cookies=session_data["cookies"],
        )

        # Retrieve CCD records from recently modified jobs.
        records = scan_recent_jobs(api)

        print(f"\nFound {len(records)} CCD items.")

        # Initialize database after a successful scan.
        initialize_database()

        results = {
            "NEW": 0,
            "COST_ADDED": 0,
            "ADJUSTED": 0,
            "UNCHANGED": 0,
            "PENDING_REVIEW": 0,
        }

        for record in records:
            result = save_damage_record(record)
            results[result] += 1

        print("\nDatabase update complete!")

        for status, count in results.items():
            print(f"{status}: {count}")

    finally:
        browser.close()


if __name__ == "__main__":
    main()

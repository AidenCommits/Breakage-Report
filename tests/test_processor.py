
from auth import ContentsTrackBrowser
from ct_api import ContentsTrackApi
from processor import scan_recent_jobs


def main():
    browser = ContentsTrackBrowser()

    try:
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

        records = scan_recent_jobs(api)

        print("\nScan complete!")
        print(f"CCD items found: {len(records)}")

        for record in records:
            print(
                f"\nItem: {record['description']}"
                f"\nJob ID: {record['job_id']}"
                f"\nStatus: {record['status']}"
                f"\nCost type: {record['cost_type']}"
                f"\nCost: {record['cost']}"
            )

    finally:
        browser.close()


if __name__ == "__main__":
    main()

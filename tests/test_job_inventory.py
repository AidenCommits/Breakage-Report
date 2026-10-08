
from urllib import response

from auth import ContentsTrackBrowser
from ct_api import ContentsTrackApi


TEST_JOB_IDS = [
    "a218ec99-d48a-494d-bca2-7eaf1882b29c",
    "7eb756bf-9d5c-4fdf-a885-96b5f1dc345e",
]


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

        for job_id in TEST_JOB_IDS:
            print(f"\nRetrieving inventory for job: {job_id}")

            response = api.get_items_for_job(job_id)

            print(f"Response type: {type(response).__name__}")
            print(f"Response keys: {list(response.keys()) if isinstance(response, dict) else 'List'}")

            items = (
                response
                if isinstance(response, list)
                else response.get("data", [])
            )

            print(f"Items retrieved: {len(items)}")

            for item in items[:3]:
                print(
                    f"Item ID: {item.get('Id')} | "
                    f"Description: {item.get('Description')}"
                )

    finally:
        browser.close()


if __name__ == "__main__":
    main()

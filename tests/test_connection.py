from auth import ContentsTrackBrowser
from ct_api import ContentsTrackAPI

def main():

    browser = ContentsTrackBrowser()

    try:

        print("Starting ContentsTrackBrowser...")
        print()
        browser.start()

        print("waiting for authentication...")
        print()

        if not browser.wait_for_api_headers(timeout=30):
            raise RuntimeError("Failed to capture authenticated API headers.")

        session_data = browser.get_api_session_data()

        api = ContentsTrackAPI(
            headers=session_data["headers"],
            cookies=session_data["cookies"]
        )

        print("Requesting Inventory...")
        print()

        response = api.get_all_items()

        if isinstance(response, list):
            items = response

        else:
            items = response.get("data", [])

        print("Connection successful!")
        print()
        print(f"Retrieved {len(items)} items.")
        print()

        ccd_id = "eff64819-ca1b-4a45-b7ec-ebbe9d59255c"

        ccd_items = [
            item for item in items
            if ccd_id in (item.get("ConditionCodeIds") or [])
        ]

        print(f"CCD items found: {len(ccd_items)}")
        print()

        for item in ccd_items:
            print("item: ", item.get("Description"))
            print("Notes: ", item.get("NotesText"))
            print()

    finally:
        browser.close()

if __name__ == "__main__":
    main()
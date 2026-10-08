from datetime import datetime, timedelta, timezone
from auth import ContentsTrackBrowser
from ct_api import ContentsTrackApi
from config import JOB_LOOKBACK_DAYS


def main():
    browser = ContentsTrackBrowser()

    try:
        print("Starting ContentsTrack browser...")
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

        print("Retrieving ContentsTrack jobs...")
        response = api.get_all_jobs()

        jobs = (
            response
            if isinstance(response, list)
            else response.get("data", [])
        )

        cutoff = datetime.now(timezone.utc) - timedelta(
            days=JOB_LOOKBACK_DAYS
        )

        recent_jobs = []

        for job in jobs:
            modified = job.get("DateModified")

            if not modified:
                continue

            modified_date = datetime.fromisoformat(
                modified.replace("Z", "+00:00")
            )

            if modified_date >= cutoff:
                recent_jobs.append(job)

        print("\nConnection successful!")
        print(f"Total jobs retrieved: {len(jobs)}")
        print(
            f"Jobs modified in the last "
            f"{JOB_LOOKBACK_DAYS} days: {len(recent_jobs)}"
        )

        print("\nRecent jobs:")

        for job in recent_jobs[:10]:
            print(
                f"Job ID: {job.get('Id')} | "
                f"Modified: {job.get('DateModified')}"
            )

    finally:
        browser.close()


if __name__ == "__main__":
    main()

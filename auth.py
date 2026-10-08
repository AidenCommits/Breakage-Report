from pathlib import Path

from playwright.sync_api import sync_playwright
import time

from config import EQUIPMENT_INVENTORY_URL


PROFILE_DIR = (
    Path(__file__).resolve().parent
    / "browser_profile"
)


class ContentsTrackBrowser:

    def __init__(self):
        self.playwright = None
        self.context = None
        self.page = None
        self.api_headers = None

    def start(self):

        self.playwright = (
            sync_playwright().start()
        )

        self.context = (
            self.playwright.chromium
            .launch_persistent_context(
                user_data_dir=PROFILE_DIR,
                headless=False,
            )
        )

        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()

        # Listen BEFORE loading ContentsTrack.
        self.page.on(
            "request",
            self._capture_api_headers
        )

        self.page.goto(
            EQUIPMENT_INVENTORY_URL,
            wait_until="domcontentloaded",
        )

        return self.page

    def wait_for_api_headers(self, timeout=15):

        start_time = time.time()

        while self.api_headers is None:

            if time.time() - start_time > timeout:
                return False

            self.page.wait_for_timeout(250)

        return True

    def _capture_api_headers(self, request):

        if (
            "/api/Item/GetAllItems"
            not in request.url
        ):
            return

        headers = request.headers

        authorization = headers.get(
            "authorization"
        )

        job = headers.get("job")

        company_id = headers.get(
            "x-company-id"
        )

        if (
            authorization
            and job
            and company_id
        ):

            self.api_headers = {
                "Authorization":
                    authorization,

                "job":
                    job,

                "X-Company-Id":
                    company_id,

                "Accept":
                    "application/json, text/plain, */*",
            }

            print(
                "Captured authenticated "
                "GetAllItems headers."
            )

    def get_api_session_data(self):

        if self.api_headers is None:
            raise RuntimeError(
                "Authenticated API headers have not been captured."
            )

        cookies = self.context.cookies()
        cookie_dict = {
            cookie["name"]: cookie["value"]
            for cookie in cookies
        }

        return {
            "headers": self.api_headers.copy(),
            "cookies": cookie_dict
        }

    def close(self):

        if self.context:
            self.context.close()

        if self.playwright:
            self.playwright.stop()

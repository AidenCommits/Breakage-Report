import requests
from config import (
    BASE_URL,
    ALL_ITEMS_ENDPOINT,
    CHAIN_OF_CUSTODY_ENDPOINT,
    REQUEST_TIMEOUT,
    ALL_JOBS_ENDPOINT,
    EQUIPMENT_JOB_ID,
    COMPANY_ID
)

class ContentsTrackApi:

    def __init__(self, headers, cookies=None):

        self.session = requests.Session()

        self.session.headers.update(headers)

        if cookies:
            self.session.cookies.update(cookies)

    def _get(self, endpoint):
        url = BASE_URL + endpoint

        response = self.session.get(
             url,
             timeout=REQUEST_TIMEOUT
         )

        response.raise_for_status()

        return response.json()

    def get_all_items(self):

        return self._get(ALL_ITEMS_ENDPOINT)

    def get_chain_of_custody(self, item_id):
        
        endpoint = (
            CHAIN_OF_CUSTODY_ENDPOINT.format(
                item_id=item_id
            )
        )

        return self._get(endpoint)

    def get_all_jobs(self):
        
        return self._get(ALL_JOBS_ENDPOINT)

    def get_items_for_job(self, job_id):
        
        """Retrieve inventory for a specific job."""
        
        headers = {"job": job_id}

        response = self.session.get(
            BASE_URL + ALL_ITEMS_ENDPOINT,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()
        return response.json()
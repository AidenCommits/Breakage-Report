from pathlib import Path
from zoneinfo import ZoneInfo

COMPANY_ID = "c7755aff-215f-44d1-b25a-066865b11cf4"
EQUIPMENT_JOB_ID = "1eb9208b-7ba7-46c1-ba65-b73eaa241c0d"
BASE_URL = "https://contentstrack.com"
EQUIPMENT_INVENTORY_URL = "https://contentstrack.com/app/companies/c7755aff-215f-44d1-b25a-066865b11cf4/jobDetails/1eb9208b-7ba7-46c1-ba65-b73eaa241c0d/inventory"
ALL_ITEMS_ENDPOINT = "/api/Item/GetAllItems"
CHAIN_OF_CUSTODY_ENDPOINT = "/api/Item/GetChainOfCustodyTimeline/{item_id}"
EQUIPMENT_BARCODE_PREFIX = "HCequipment-"
HOME_LOCATION = "Chem Room"
LOCAL_TIMEZONE = ZoneInfo("America/New_York")
REQUEST_TIMEOUT = 30
CCD_CONDITION_ID = "eff64819-ca1b-4a45-b7ec-ebbe9d59255c"

BASE_DIR = Path(__file__).resolve().parent
REPORT_DIR = BASE_DIR / "reports"

REPORT_DIR.mkdir(exist_ok=True)
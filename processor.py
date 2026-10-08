from datetime import datetime, timedelta, timezone
from config import CCD_CONDITION_ID, JOB_LOOKBACK_DAYS
from cost_parser import parse_damage_cost

def get_recent_jobs(jobs, lookback_days=JOB_LOOKBACK_DAYS):
    """Return jobs modified within the lookback period."""

    cutoff = datetime.now(timezone.utc) - timedelta(
        days=lookback_days
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

    return recent_jobs

def process_job(api, job):
    """Find and process CCD items belonging to one job."""

    response = api.get_items_for_job(job["Id"])

    items = (
        response
        if isinstance(response, list)
        else response.get("data", [])
    )

    damage_records = []

    for item in items:
        condition_ids = item.get("ConditionCodeIds") or []

        if CCD_CONDITION_ID not in condition_ids:
            continue

        parsed_cost = parse_damage_cost(
            item.get("NotesText", [])
        )

        damage_records.append({
            "job_id": job["Id"],
            "job_name": job.get("Name"),
            "item_id": item["Id"],
            "description": item.get("Description"),
            "room": item.get("Room"),
            "quantity": item.get("Quantity"),
            "cost_type": parsed_cost["cost_type"],
            "cost": parsed_cost["cost"],
            "status": parsed_cost["status"],
        })

    return damage_records

def scan_recent_jobs(api):
    """Scan recently modified jobs for CCD items."""

    response = api.get_all_jobs()

    jobs = (
        response
        if isinstance(response, list)
        else response.get("data", [])
    )

    recent_jobs = get_recent_jobs(jobs)

    all_damage = []

    print(f"Scanning {len(recent_jobs)} recent jobs...")

    for index, job in enumerate(recent_jobs, start=1):
        print(
            f"[{index}/{len(recent_jobs)}] "
            f"Scanning job {job['Id']}"
        )

        records = process_job(api, job)
        all_damage.extend(records)

    return all_damage

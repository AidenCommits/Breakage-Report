import re
from decimal import Decimal, InvalidOperation

COST_PATTERNS = {
    "REPLACEMENT": re.compile(
        r"\bReplacement\s+Cost\s*:\s*\$?\s*"
        r"(\d[\d,]*(?:\.\d{1,2})?)\b",
        re.IGNORECASE,
    ),
    "REPAIR": re.compile(
        r"\bRepair\s+Cost\s*:\s*\$?\s*"
        r"(\d[\d,]*(?:\.\d{1,2})?)\b",
        re.IGNORECASE,
    )
}

def parse_damage_cost(notes):
    """
    Extract a repair or replacement cost from
    ContentsTrack item notes.

    Returns:
        {
            "status": "READY" | "PENDING" | "REVIEW",
            "cost_type": str | None,
            "cost": Decimal | None,
        }
    """

    matches = []

    for note in notes or []:
        if not isinstance(note, str):
            continue

        for cost_type, pattern in COST_PATTERNS.items():
            for match in pattern.finditer(note):
                try:
                    cost = Decimal(
                        match.group(1).replace(",", "")
                    )
                except InvalidOperation:
                    continue

                matches.append((cost_type, cost))

    if not matches:
        return {
            "status": "PENDING",
            "cost_type": None,
            "cost": None,
        }

    if len(matches) != 1:
        return {
            "status": "REVIEW",
            "cost_type": None,
            "cost": None,
        }

    cost_type, cost = matches[0]

    return {
        "status": "READY",
        "cost_type": cost_type,
        "cost": cost,
    }

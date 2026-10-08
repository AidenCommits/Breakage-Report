from decimal import Decimal
from cost_parser import parse_damage_cost

def test_repair_cost():
    notes = [
        "Purple splotches on right side of front",
        "Repair Cost: 25",
    ]

    result = parse_damage_cost(notes)

    assert result["status"] == "READY"
    assert result["cost_type"] == "REPAIR"
    assert result["cost"] == Decimal("25")

def test_replacement_cost():
    notes = ["Replacement Cost: $50"]

    result = parse_damage_cost(notes)

    assert result["status"] == "READY"
    assert result["cost_type"] == "REPLACEMENT"
    assert result["cost"] == Decimal("50")

def test_missing_cost():
    notes = ["Item was damaged during transport"]

    result = parse_damage_cost(notes)

    assert result["status"] == "PENDING"
    assert result["cost"] is None

def test_conflicting_costs():
    notes = [
        "Repair Cost: 25",
        "Replacement Cost: 50",
    ]

    result = parse_damage_cost(notes)

    assert result["status"] == "REVIEW"
    assert result["cost"] is None

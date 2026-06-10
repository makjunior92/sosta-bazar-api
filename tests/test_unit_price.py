from decimal import Decimal

from app.services.unit_price import compute_unit_price, extract_unit_info, parse_price


def test_parse_price():
    assert parse_price("৳ 125") == Decimal("125")
    assert parse_price("1,250.50") == Decimal("1250.50")


def test_extract_unit_info():
    label, size = extract_unit_info("Pran Butter 200g")
    assert label == "g"
    assert size == Decimal("200")


def test_compute_unit_price():
    price = Decimal("200")
    unit = compute_unit_price(price, "Pran Butter 200g")
    assert unit == Decimal("1000.0000")

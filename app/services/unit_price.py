import re
from decimal import Decimal, InvalidOperation

UNIT_PATTERNS = [
    (re.compile(r"(\d+(?:\.\d+)?)\s*kg", re.I), "kg", 1000),
    (re.compile(r"(\d+(?:\.\d+)?)\s*g\b", re.I), "g", 1),
    (re.compile(r"(\d+(?:\.\d+)?)\s*l\b", re.I), "L", 1000),
    (re.compile(r"(\d+(?:\.\d+)?)\s*ml", re.I), "ml", 1),
    (re.compile(r"(\d+)\s*(?:pcs|pc|piece|pieces)\b", re.I), "piece", 1),
]


def parse_price(text: str) -> Decimal | None:
    cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def extract_unit_info(title: str) -> tuple[str | None, Decimal | None]:
    for pattern, label, _ in UNIT_PATTERNS:
        match = pattern.search(title)
        if match:
            size = Decimal(match.group(1))
            return label, size
    return None, None


def compute_unit_price(price: Decimal, title: str) -> Decimal | None:
    label, size = extract_unit_info(title)
    if not label or not size or size == 0:
        return None
    if label == "kg":
        return (price / size).quantize(Decimal("0.0001"))
    if label == "g":
        return (price / (size / Decimal(1000))).quantize(Decimal("0.0001"))
    if label == "L":
        return (price / size).quantize(Decimal("0.0001"))
    if label == "ml":
        return (price / (size / Decimal(1000))).quantize(Decimal("0.0001"))
    return (price / size).quantize(Decimal("0.0001"))

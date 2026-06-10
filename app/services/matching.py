import re
from decimal import Decimal

from thefuzz import fuzz

from app.scrapers.base import RawOffer
from app.services.unit_price import compute_unit_price, extract_unit_info

# Product types that follow the query word → usually NOT the base product (e.g. "milk chocolate")
COMPOUND_SUFFIXES = (
    "chocolate",
    "butter",
    "biscuit",
    "biscuits",
    "cookie",
    "cookies",
    "candy",
    "bar",
    "bars",
    "bread",
    "cake",
    "cakes",
    "cereal",
    "spread",
    "snack",
    "snacks",
    "wafer",
    "wafers",
    "toffee",
    "caramel",
    "maid",
    "shake",
    "shakes",
    "powder",
    "food",
    "cream biscuit",
    "tea",
    "coffee",
)

# Modifiers before query that suggest a compound product (e.g. "chocolate milk drink")
COMPOUND_PREFIXES = (
    "chocolate",
    "cocoa",
    "dark",
    "white",
    "strawberry",
    "vanilla",
    "malted",
    "condensed",
    "coconut",
    "soy",
    "soya",
    "almond",
    "oat",
)

# Signals the product IS the searched grocery item (e.g. liquid milk, fresh rice)
PRIMARY_PRODUCT_SIGNALS = (
    "liquid",
    "fresh",
    "pasteurised",
    "pasteurized",
    "uht",
    "full cream",
    "toned",
    "skim",
    "low fat",
    "whole",
    "premium",
    "miniket",
    "nazirshail",
    "chinigura",
    "atop",
    "parboiled",
    "basmati",
    "polao",
    "jeera",
    "raw",
    "organic",
    "farm",
)

SIZE_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(kg|g|l|ltr|litre|liter|ml|pcs|pc|piece|pieces)\b",
    re.I,
)


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


def score_relevance(query: str, title: str) -> int:
    """
    Score how closely a product title matches the search intent.
    100 = exact product (e.g. milk for 'milk'), 25-40 = related compound, 10 = weak match, 0 = no match.
    """
    q = normalize_title(query)
    t = normalize_title(title)
    if not q:
        return 0

    # Must contain query as substring at minimum
    if q not in t:
        return 0

    # Substring only (e.g. "milky") — weak
    if not re.search(rf"\b{re.escape(q)}\b", t):
        return 10

    # Compound: "milk chocolate", "milk butter"
    for suffix in COMPOUND_SUFFIXES:
        if re.search(rf"\b{re.escape(q)}\s+{suffix}\b", t):
            return 30
        if re.search(rf"\b{suffix}\s+{re.escape(q)}\b", t):
            return 35

    for prefix in COMPOUND_PREFIXES:
        if re.search(rf"\b{prefix}\s+.*\b{re.escape(q)}\b", t):
            return 35

    # Brand names where query is not the product type
    brand_compounds = ("dairy milk", "milk vita")  # Cadbury Dairy Milk = chocolate
    for brand in brand_compounds:
        if brand in t and q in brand:
            return 25

    score = 60

    # Title leads with the query → strong signal ("Milk 1L", "Rice Premium")
    if re.match(rf"^{re.escape(q)}\b", t):
        score += 25

    # Primary grocery signals (liquid milk, premium rice, etc.)
    if any(signal in t for signal in PRIMARY_PRODUCT_SIGNALS):
        score += 15

    # Has a size unit → likely the actual product listing
    if SIZE_PATTERN.search(t):
        score += 10

    # Penalize long titles with many words (often processed foods)
    word_count = len(t.split())
    if word_count > 8:
        score -= 10

    return min(max(score, 1), 100)


def partition_offers(query: str, offers: list[dict], exact_threshold: int = 65) -> tuple[list[dict], list[dict]]:
    """Split offers into exact matches and related products."""
    exact: list[dict] = []
    related: list[dict] = []

    for offer in offers:
        title = offer.get("title", "")
        score = score_relevance(query, title)
        offer = {**offer, "relevance_score": score}
        if score >= exact_threshold:
            exact.append(offer)
        elif score > 0:
            related.append(offer)

    def price_key(o: dict) -> tuple:
        unit = o.get("unit_price_bdt")
        price = o.get("price_bdt", "999999")
        rel = o.get("relevance_score", 0)
        return (-rel, unit if unit is not None else price, price)

    exact.sort(key=price_key)
    related.sort(key=price_key)
    return exact, related


def group_offers_by_product(offers: list[RawOffer], threshold: int = 75) -> list[list[RawOffer]]:
    groups: list[list[RawOffer]] = []
    used: set[int] = set()

    for i, offer in enumerate(offers):
        if i in used:
            continue
        group = [offer]
        used.add(i)
        for j, other in enumerate(offers):
            if j in used or i == j:
                continue
            score = fuzz.token_sort_ratio(normalize_title(offer.title), normalize_title(other.title))
            if score >= threshold:
                group.append(other)
                used.add(j)
        groups.append(group)
    return groups


def enrich_offer(offer: RawOffer) -> RawOffer:
    if offer.unit_price_bdt is None:
        offer.unit_price_bdt = compute_unit_price(offer.price_bdt, offer.title)
    return offer


def mark_best_deals(offers: list[dict]) -> list[dict]:
    if not offers:
        return offers

    def sort_key(o: dict) -> tuple:
        unit = o.get("unit_price_bdt")
        price = o.get("price_bdt", Decimal("999999"))
        return (unit if unit is not None else price, price)

    sorted_offers = sorted(offers, key=sort_key)
    best = sorted_offers[0]
    best_key = (best.get("unit_price_bdt"), best.get("price_bdt"))
    for o in offers:
        o["is_best_deal"] = (
            o.get("unit_price_bdt") == best_key[0] and o.get("price_bdt") == best_key[1]
        )
    return offers

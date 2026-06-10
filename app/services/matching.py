import re
from decimal import Decimal

from thefuzz import fuzz

from app.scrapers.base import RawOffer
from app.services.unit_price import compute_unit_price, extract_unit_info


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


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

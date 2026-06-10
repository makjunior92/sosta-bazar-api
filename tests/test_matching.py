from app.services.matching import mark_best_deals
from decimal import Decimal


def test_mark_best_deals():
    offers = [
        {"price_bdt": Decimal("300"), "unit_price_bdt": Decimal("150"), "title": "A"},
        {"price_bdt": Decimal("200"), "unit_price_bdt": Decimal("100"), "title": "B"},
    ]
    result = mark_best_deals(offers)
    assert result[1]["is_best_deal"] is True
    assert result[0]["is_best_deal"] is False

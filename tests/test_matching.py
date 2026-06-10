from app.services.matching import mark_best_deals, score_relevance


def test_milk_exact_vs_chocolate():
    assert score_relevance("milk", "Pran Fresh Milk 1 L") >= 65
    assert score_relevance("milk", "ACI Liquid Milk 1L") >= 65
    assert score_relevance("milk", "Milk Chocolate Bar 80g") < 65
    assert score_relevance("milk", "Cadbury Dairy Milk Chocolate") < 65
    assert score_relevance("milk", "Milk Butter Spread 200g") < 65


def test_rice_exact_vs_compound():
    assert score_relevance("rice", "Chinigura Rice Premium 1 kg") >= 65
    assert score_relevance("rice", "Miniket Rice Premium 5 kg") >= 65


def test_mark_best_deals():
    from decimal import Decimal

    offers = [
        {"price_bdt": Decimal("300"), "unit_price_bdt": Decimal("150"), "title": "A"},
        {"price_bdt": Decimal("200"), "unit_price_bdt": Decimal("100"), "title": "B"},
    ]
    result = mark_best_deals(offers)
    assert result[1]["is_best_deal"] is True
    assert result[0]["is_best_deal"] is False

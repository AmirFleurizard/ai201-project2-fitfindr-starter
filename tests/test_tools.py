"""
tests/test_tools.py

Pytest tests for the three FitFindr tools, covering both happy paths
and failure modes.
"""

import pytest
from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── search_listings tests ───────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)

def test_search_results_have_required_fields():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    required_fields = {"id", "title", "description", "category", "style_tags",
                        "size", "condition", "price", "colors", "brand", "platform"}
    for item in results:
        assert required_fields.issubset(item.keys())


# ── suggest_outfit tests ────────────────────────────────────────────────────

def test_suggest_outfit_with_wardrobe():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    suggestion = suggest_outfit(results[0], get_example_wardrobe())
    assert isinstance(suggestion, str)
    assert len(suggestion) > 0

def test_suggest_outfit_empty_wardrobe():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    suggestion = suggest_outfit(results[0], get_empty_wardrobe())
    assert isinstance(suggestion, str)
    assert len(suggestion) > 0  # should NOT be empty or crash


# ── create_fit_card tests ───────────────────────────────────────────────────

def test_create_fit_card_with_valid_outfit():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    outfit = suggest_outfit(results[0], get_example_wardrobe())
    fit_card = create_fit_card(outfit, results[0])
    assert isinstance(fit_card, str)
    assert len(fit_card) > 0

def test_create_fit_card_empty_outfit():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    fit_card = create_fit_card("", results[0])
    assert fit_card == "Could not generate a fit card — outfit description was missing."

def test_create_fit_card_varies_output():
    """Verify the fit card produces different output for different runs (temperature check)."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    outfit = suggest_outfit(results[0], get_example_wardrobe())
    card1 = create_fit_card(outfit, results[0])
    card2 = create_fit_card(outfit, results[0])
    assert card1 != card2  # should differ due to LLM temperature
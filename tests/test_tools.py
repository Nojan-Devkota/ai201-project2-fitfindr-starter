"""Tests for FitFindr tools."""

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    results = search_listings("track jacket", size="M", max_price=100)
    assert all("M" in item["size"].upper() for item in results)


def test_create_fit_card_empty_outfit():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    message = create_fit_card("", results[0])
    assert "Cannot create a fit card" in message


def test_suggest_outfit_empty_wardrobe():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    advice = suggest_outfit(results[0], get_empty_wardrobe())
    assert isinstance(advice, str)
    assert len(advice) > 0

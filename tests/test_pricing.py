"""Tests unitarios para utils/pricing.py"""
import pytest
from utils.pricing import pos, pick_prices


# ---------------------------------------------------------------------------
# pos — extrae precio positivo de distintos tipos de entrada
# ---------------------------------------------------------------------------

def test_pos_float():
    assert pos(99.9) == 99.9

def test_pos_int():
    assert pos(100) == 100.0

def test_pos_zero_returns_none():
    assert pos(0) is None
    assert pos(0.0) is None

def test_pos_negative_returns_none():
    assert pos(-1.5) is None

def test_pos_none():
    assert pos(None) is None

def test_pos_string_plain():
    assert pos("99.99") == 99.99

def test_pos_string_comma():
    assert pos("1.234,50") == 1234.50

def test_pos_string_zero():
    assert pos("0") is None
    assert pos("0.0") is None
    assert pos("0,0") is None

def test_pos_string_empty():
    assert pos("") is None

def test_pos_dict_with_value_key():
    assert pos({"value": 50.0}) == 50.0

def test_pos_dict_with_price_key():
    assert pos({"price": 75.5}) == 75.5

def test_pos_dict_with_list_price():
    assert pos({"ListPrice": 120.0}) == 120.0

def test_pos_dict_with_spot_price():
    assert pos({"spotPrice": 89.0}) == 89.0

def test_pos_dict_empty():
    assert pos({}) is None

def test_pos_nested_dict():
    assert pos({"value": {"price": 55.0}}) == 55.0


# ---------------------------------------------------------------------------
# pick_prices — extrae effective y regular price de un offer dict
# ---------------------------------------------------------------------------

def test_pick_prices_with_list_price():
    offer = {"ListPrice": 100.0, "spotPrice": 80.0, "Price": 80.0}
    effective, regular = pick_prices(offer)
    # ListPrice es el precio de lista; effective = regular cuando no hay descuento explícito
    assert regular == 100.0
    assert effective == 100.0

def test_pick_prices_without_list_price():
    offer = {"spotPrice": 80.0, "Price": 80.0}
    effective, regular = pick_prices(offer)
    assert effective == 80.0
    assert regular == 80.0

def test_pick_prices_with_price_without_discount():
    offer = {"PriceWithoutDiscount": 150.0, "spotPrice": 120.0}
    effective, regular = pick_prices(offer)
    assert regular == 150.0

def test_pick_prices_empty_offer():
    assert pick_prices({}) == (None, None)

def test_pick_prices_none_offer():
    assert pick_prices(None) == (None, None)

def test_pick_prices_all_zero():
    # Precios en 0 se tratan como None por pos()
    offer = {"ListPrice": 0, "spotPrice": 0, "Price": 0}
    assert pick_prices(offer) == (None, None)

def test_pick_prices_only_selling_price():
    offer = {"sellingPrice": 55.0}
    effective, regular = pick_prices(offer)
    assert effective == 55.0
    assert regular == 55.0

"""Tests unitarios para funciones helper de data/db.py"""
import pytest
from decimal import Decimal
from data.db import (
    _normalize_ean,
    _to_decimal,
    _to_int,
    _build_source_product_id,
    _build_extra,
    _market_meta,
)


# ---------------------------------------------------------------------------
# _normalize_ean
# ---------------------------------------------------------------------------

def test_normalize_ean_valid_13_digits():
    assert _normalize_ean("7790895000997") == "7790895000997"

def test_normalize_ean_valid_8_digits():
    assert _normalize_ean("12345678") == "12345678"

def test_normalize_ean_valid_14_digits():
    assert _normalize_ean("12345678901234") == "12345678901234"

def test_normalize_ean_strips_non_digits():
    # Si viene con guiones u otros chars, los filtra
    assert _normalize_ean("779-089-5000997") == "7790895000997"

def test_normalize_ean_too_short():
    assert _normalize_ean("123") is None

def test_normalize_ean_too_long():
    assert _normalize_ean("123456789012345") is None  # 15 dígitos

def test_normalize_ean_none():
    assert _normalize_ean(None) is None

def test_normalize_ean_empty():
    assert _normalize_ean("") is None


# ---------------------------------------------------------------------------
# _to_decimal
# ---------------------------------------------------------------------------

def test_to_decimal_float():
    assert _to_decimal(99.99) == Decimal("99.99")

def test_to_decimal_string():
    assert _to_decimal("1234.56") == Decimal("1234.56")

def test_to_decimal_int():
    assert _to_decimal(100) == Decimal("100")

def test_to_decimal_none():
    assert _to_decimal(None) is None

def test_to_decimal_empty_string():
    assert _to_decimal("") is None

def test_to_decimal_invalid():
    assert _to_decimal("no-es-un-numero") is None


# ---------------------------------------------------------------------------
# _to_int
# ---------------------------------------------------------------------------

def test_to_int_string():
    assert _to_int("42") == 42

def test_to_int_float_string():
    # _to_int usa int(value) directamente: "3.0" no es un int válido en Python
    assert _to_int("3.0") is None

def test_to_int_none():
    assert _to_int(None) is None

def test_to_int_empty():
    assert _to_int("") is None

def test_to_int_invalid():
    assert _to_int("abc") is None


# ---------------------------------------------------------------------------
# _build_source_product_id
# ---------------------------------------------------------------------------

def test_build_source_product_id_uses_product_reference():
    product = {"productReference": "REF123", "itemId": "ITEM456"}
    assert _build_source_product_id(product) == "REF123"

def test_build_source_product_id_falls_back_to_item_id():
    product = {"itemId": "ITEM456", "productId": "PROD789"}
    assert _build_source_product_id(product) == "ITEM456"

def test_build_source_product_id_falls_back_to_ean():
    product = {"ean": "7790895000997"}
    assert _build_source_product_id(product) == "7790895000997"

def test_build_source_product_id_fallback_hash():
    product = {"someUnknownField": "value"}
    result = _build_source_product_id(product)
    assert result.startswith("fallback:")
    assert len(result) > len("fallback:")

def test_build_source_product_id_consistent_hash():
    product = {"someUnknownField": "value"}
    # Mismo input → mismo hash
    assert _build_source_product_id(product) == _build_source_product_id(product)


# ---------------------------------------------------------------------------
# _build_extra
# ---------------------------------------------------------------------------

def test_build_extra_excludes_known_fields():
    product = {
        "name": "Leche",
        "ean": "123456789012",
        "customField": "custom_value",
    }
    extra = _build_extra(product)
    assert "name" not in extra
    assert "ean" not in extra
    assert extra["customField"] == "custom_value"

def test_build_extra_excludes_none_values():
    product = {"customField": None, "otherField": "value"}
    extra = _build_extra(product)
    assert "customField" not in extra
    assert extra["otherField"] == "value"

def test_build_extra_empty_product():
    assert _build_extra({}) == {}


# ---------------------------------------------------------------------------
# _market_meta
# ---------------------------------------------------------------------------

def test_market_meta_known_market():
    meta = _market_meta("carrefour", None)
    assert meta["code"] == "carrefour"
    assert meta["name"] == "Carrefour"
    assert "carrefour.com.ar" in meta["base_url"]

def test_market_meta_override_url():
    meta = _market_meta("coto", "https://custom.url")
    assert meta["base_url"] == "https://custom.url"

def test_market_meta_unknown_market():
    meta = _market_meta("supermercado_x", None)
    assert meta["code"] == "supermercado_x"
    assert meta["name"] == "Supermercado_X"

def test_market_meta_empty_code():
    meta = _market_meta("", None)
    assert meta["code"] == "unknown"

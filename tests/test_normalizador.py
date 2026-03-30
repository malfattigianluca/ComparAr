"""Tests unitarios para utils/normalizador.py"""
import pytest
from utils.normalizador import (
    normalize_text,
    extract_unit,
    to_float,
    safe_div,
    parse_content,
    normalize_amount_unit,
)


# ---------------------------------------------------------------------------
# normalize_text
# ---------------------------------------------------------------------------

def test_normalize_text_lowercase():
    assert normalize_text("Leche ENTERA") == "leche entera"

def test_normalize_text_comma_to_dot():
    assert normalize_text("1,5 lt") == "1.5 lt"

def test_normalize_text_collapses_whitespace():
    assert normalize_text("  hola   mundo  ") == "hola mundo"


# ---------------------------------------------------------------------------
# extract_unit
# ---------------------------------------------------------------------------

def test_extract_unit_litro():
    assert extract_unit("1 litro") == "lt"

def test_extract_unit_ml():
    assert extract_unit("500 ml") == "ml"

def test_extract_unit_kg():
    assert extract_unit("1.5 kg") == "kg"

def test_extract_unit_gramos():
    assert extract_unit("250 gramos") == "g"

def test_extract_unit_unidades():
    assert extract_unit("12 unidades") == "unit"

def test_extract_unit_none_when_no_match():
    # "unidad" matchea el alias de "unit", así que retorna "unit"
    assert extract_unit("sin unidad") == "unit"

def test_extract_unit_none_when_truly_no_match():
    assert extract_unit("sin medida aqui") is None

def test_extract_unit_empty_string():
    assert extract_unit("") is None


# ---------------------------------------------------------------------------
# to_float
# ---------------------------------------------------------------------------

def test_to_float_simple():
    assert to_float("1.5") == 1.5

def test_to_float_european_comma():
    assert to_float("1,5") == 1.5

def test_to_float_european_thousands():
    assert to_float("1.234,56") == 1234.56

def test_to_float_with_text():
    assert to_float("precio: 123.45 pesos") == 123.45

def test_to_float_none():
    assert to_float(None) is None

def test_to_float_no_number():
    assert to_float("sin precio") is None


# ---------------------------------------------------------------------------
# safe_div
# ---------------------------------------------------------------------------

def test_safe_div_normal():
    assert safe_div(10, 2) == 5.0

def test_safe_div_none_numerator():
    assert safe_div(None, 2) is None

def test_safe_div_zero_denominator():
    assert safe_div(10, 0) is None

def test_safe_div_none_denominator():
    assert safe_div(10, None) is None


# ---------------------------------------------------------------------------
# parse_content
# ---------------------------------------------------------------------------

def test_parse_content_simple_ml():
    amount, unit, packs = parse_content("Leche Entera 1L")
    assert unit == "lt"
    assert amount == 1.0
    assert packs == 1

def test_parse_content_grams():
    amount, unit, packs = parse_content("Arroz 500g")
    assert unit == "g"
    assert amount == 500.0
    assert packs == 1

def test_parse_content_pack():
    amount, unit, packs = parse_content("Agua mineral 6 x 500ml")
    assert packs == 6
    assert amount == 3000.0
    assert unit == "ml"

def test_parse_content_kg():
    amount, unit, packs = parse_content("Harina 1kg")
    assert unit == "kg"
    assert amount == 1.0

def test_parse_content_no_unit():
    amount, unit, packs = parse_content("Yerba Mate")
    assert amount is None
    assert unit is None
    assert packs == 1

def test_parse_content_empty():
    assert parse_content("") == (None, None, 1)
    assert parse_content(None) == (None, None, 1)


# ---------------------------------------------------------------------------
# normalize_amount_unit
# ---------------------------------------------------------------------------

def test_normalize_liters_to_ml():
    amount, unit = normalize_amount_unit(1.5, "lt")
    assert amount == 1500.0
    assert unit == "ml"

def test_normalize_l_to_ml():
    amount, unit = normalize_amount_unit(2, "l")
    assert amount == 2000.0
    assert unit == "ml"

def test_normalize_cc_to_ml():
    amount, unit = normalize_amount_unit(330, "cc")
    assert amount == 330
    assert unit == "ml"

def test_normalize_kg_to_g():
    amount, unit = normalize_amount_unit(1, "kg")
    assert amount == 1000.0
    assert unit == "g"

def test_normalize_gr_to_g():
    amount, unit = normalize_amount_unit(250, "gr")
    assert amount == 250
    assert unit == "g"

def test_normalize_g_unchanged():
    amount, unit = normalize_amount_unit(500, "g")
    assert amount == 500
    assert unit == "g"

def test_normalize_none_passthrough():
    assert normalize_amount_unit(None, "ml") == (None, "ml")
    assert normalize_amount_unit(500, None) == (500, None)

"""Tests unitarios para scrapers/coto_scraper.py"""
import pytest
from scrapers.coto_scraper import (
    parse_int,
    parse_float,
    get_attr,
    is_weighable_kg,
    parse_measurement_and_multiplier,
    parse_units_per_pack,
    parse_contenido_pack,
    extract_price_from_text,
    extract_discount_price,
    base_factor_from_total,
    build_category_path_coto,
)


# ---------------------------------------------------------------------------
# parse_int / parse_float
# ---------------------------------------------------------------------------

def test_parse_int_normal():
    assert parse_int("5") == 5

def test_parse_int_float_string():
    assert parse_int("3.7") == 3

def test_parse_int_invalid_returns_default():
    assert parse_int("abc") == 0
    assert parse_int(None) == 0

def test_parse_float_normal():
    assert parse_float("1.5") == 1.5

def test_parse_float_comma():
    assert parse_float("1,5") == 1.5

def test_parse_float_none_returns_default():
    assert parse_float(None) is None

def test_parse_float_invalid_returns_default():
    assert parse_float("abc") is None


# ---------------------------------------------------------------------------
# get_attr
# ---------------------------------------------------------------------------

def test_get_attr_exists():
    attrs = {"product.name": ["Leche"]}
    assert get_attr(attrs, "product.name") == "Leche"

def test_get_attr_missing():
    assert get_attr({}, "product.name") is None

def test_get_attr_empty_list():
    attrs = {"product.name": []}
    assert get_attr(attrs, "product.name") is None


# ---------------------------------------------------------------------------
# is_weighable_kg
# ---------------------------------------------------------------------------

def test_is_weighable_kg_by_flag():
    attrs = {"product.unidades.esPesable": ["1"]}
    assert is_weighable_kg(attrs) is True

def test_is_weighable_kg_by_desc_unidad():
    attrs = {"product.unidades.descUnidad": ["KGS"]}
    assert is_weighable_kg(attrs) is True

def test_is_weighable_kg_by_name():
    assert is_weighable_kg({}, name="Queso x kg") is True

def test_is_weighable_kg_false():
    attrs = {"product.unidades.esPesable": ["0"]}
    assert is_weighable_kg(attrs) is False


# ---------------------------------------------------------------------------
# parse_measurement_and_multiplier
# ---------------------------------------------------------------------------

def test_parse_measurement_500ml():
    unit, amount = parse_measurement_and_multiplier("500ml")
    assert unit == "ml"
    assert amount == 500.0

def test_parse_measurement_1kg():
    unit, amount = parse_measurement_and_multiplier("1kg")
    assert unit == "kg"
    assert amount == 1.0

def test_parse_measurement_250g():
    unit, amount = parse_measurement_and_multiplier("250g")
    assert unit == "g"
    assert amount == 250.0

def test_parse_measurement_1lt():
    unit, amount = parse_measurement_and_multiplier("1lt")
    assert unit == "lt"
    assert amount == 1.0

def test_parse_measurement_no_match():
    unit, amount = parse_measurement_and_multiplier("sin unidad")
    assert unit == "unit"
    assert amount == 1.0

def test_parse_measurement_none():
    unit, amount = parse_measurement_and_multiplier(None)
    assert unit == "unit"
    assert amount == 1.0


# ---------------------------------------------------------------------------
# parse_units_per_pack
# ---------------------------------------------------------------------------

def test_parse_units_per_pack_unidades():
    assert parse_units_per_pack("12 unidades") == 12

def test_parse_units_per_pack_x_format():
    assert parse_units_per_pack("x6") == 6

def test_parse_units_per_pack_no_match():
    assert parse_units_per_pack("sin pack") is None

def test_parse_units_per_pack_none():
    assert parse_units_per_pack(None) is None


# ---------------------------------------------------------------------------
# parse_contenido_pack
# ---------------------------------------------------------------------------

def test_parse_contenido_pack_with_units():
    unit_amt, unit, upp, total = parse_contenido_pack("500ml x 6 unidades")
    assert unit == "ml"
    assert unit_amt == 500.0
    assert upp == 6
    assert total == 3000.0

def test_parse_contenido_pack_single():
    unit_amt, unit, upp, total = parse_contenido_pack("1lt")
    assert unit == "lt"
    assert upp == 1

def test_parse_contenido_pack_no_unit():
    result = parse_contenido_pack("sin contenido")
    assert result == (None, None, None, None)

def test_parse_contenido_pack_none():
    assert parse_contenido_pack(None) == (None, None, None, None)


# ---------------------------------------------------------------------------
# extract_price_from_text
# ---------------------------------------------------------------------------

def test_extract_price_from_text_simple():
    assert extract_price_from_text("$1.851,20 c/u") == 1851.20

def test_extract_price_from_text_precio_contado():
    assert extract_price_from_text("Precio Contado: $2848") == 2848.0

def test_extract_price_from_text_with_spaces():
    assert extract_price_from_text("Precio: $ 2.999,99") == 2999.99

def test_extract_price_from_text_none():
    assert extract_price_from_text(None) is None

def test_extract_price_from_text_empty():
    assert extract_price_from_text("") is None

def test_extract_price_from_text_no_number():
    assert extract_price_from_text("sin precio") is None


# ---------------------------------------------------------------------------
# extract_discount_price
# ---------------------------------------------------------------------------

import json

def test_extract_discount_price_valid():
    import json
    discount_data = [{"precioDescuento": "$1500,00"}]
    attrs = {"product.dtoDescuentos": [json.dumps(discount_data)]}
    result = extract_discount_price(attrs)
    assert result == 1500.0

def test_extract_discount_price_percentage_ignored():
    discount_data = [{"precioDescuento": "50% 2da unidad"}]
    attrs = {"product.dtoDescuentos": [json.dumps(discount_data)]}
    assert extract_discount_price(attrs) is None

def test_extract_discount_price_empty_attrs():
    assert extract_discount_price({}) is None

def test_extract_discount_price_empty_list():
    assert extract_discount_price({"product.dtoDescuentos": []}) is None


# ---------------------------------------------------------------------------
# base_factor_from_total
# ---------------------------------------------------------------------------

def test_base_factor_grams():
    assert base_factor_from_total("g", 500) == 0.5

def test_base_factor_kg():
    assert base_factor_from_total("kg", 2) == 2.0

def test_base_factor_ml():
    assert base_factor_from_total("ml", 1000) == 1.0

def test_base_factor_none_amount():
    assert base_factor_from_total("g", None) is None

def test_base_factor_unknown_unit():
    assert base_factor_from_total("piezas", 3) is None


# ---------------------------------------------------------------------------
# build_category_path_coto
# ---------------------------------------------------------------------------

def test_build_category_path_normal():
    result = build_category_path_coto(["Almacén", "Arroz"])
    assert result == "/Almacén/Arroz/"

def test_build_category_path_filters_blacklist():
    result = build_category_path_coto(["CotoDigital", "Home", "Bebidas"])
    assert "CotoDigital" not in result
    assert "Home" not in result
    assert "Bebidas" in result

def test_build_category_path_dedupes():
    result = build_category_path_coto(["Almacén", "Almacén", "Arroz"])
    assert result.count("Almacén") == 1

def test_build_category_path_none():
    assert build_category_path_coto(None) is None

def test_build_category_path_empty():
    assert build_category_path_coto([]) is None

def test_build_category_path_all_blacklisted():
    assert build_category_path_coto(["CotoDigital", "Home"]) is None

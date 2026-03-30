from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

try:
    import psycopg
    from psycopg.types.json import Jsonb
except Exception:  # pragma: no cover - handled at runtime
    psycopg = None
    Jsonb = None


DB_ENV_VARS = ("COMPARAR_DATABASE_URL", "DATABASE_URL")
SCHEMA_PATH = Path(__file__).with_name("schema.sql")

# Evita re-aplicar el schema en cada llamada a persist_market_snapshot.
# Se marca True la primera vez que se ejecuta exitosamente.
_schema_applied = False

MARKETS = {
    "carrefour": {
        "code": "carrefour",
        "name": "Carrefour",
        "base_url": "https://www.carrefour.com.ar",
    },
    "dia": {
        "code": "dia",
        "name": "Dia",
        "base_url": "https://diaonline.supermercadosdia.com.ar",
    },
    "coto": {
        "code": "coto",
        "name": "Coto",
        "base_url": "https://www.cotodigital.com.ar",
    },
}

UPSERT_SUPERMARKET = """
INSERT INTO supermarket (code, name, base_url, is_active)
VALUES (%s, %s, %s, TRUE)
ON CONFLICT (code)
DO UPDATE SET
    name = EXCLUDED.name,
    base_url = EXCLUDED.base_url,
    is_active = TRUE
RETURNING id;
"""

UPSERT_PRODUCT = """
INSERT INTO products (ean, name, brand, content_amount, content_unit, envase, updated_at)
VALUES (%s, %s, %s, %s, %s, %s, now())
ON CONFLICT (ean)
DO UPDATE SET
    name = EXCLUDED.name,
    brand = EXCLUDED.brand,
    content_amount = COALESCE(EXCLUDED.content_amount, products.content_amount),
    content_unit = COALESCE(EXCLUDED.content_unit, products.content_unit),
    envase = COALESCE(EXCLUDED.envase, products.envase),
    updated_at = now()
RETURNING id;
"""

UPSERT_LISTING = """
INSERT INTO listings (
    supermarket_id,
    source_product_id,
    product_id,
    ean,
    name,
    brand,
    brand_id,
    url_web,
    image_url,
    category,
    category_path,
    envase,
    measurement_unit,
    unit_multiplier,
    extra,
    created_at,
    updated_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
ON CONFLICT (supermarket_id, source_product_id)
DO UPDATE SET
    product_id = COALESCE(EXCLUDED.product_id, listings.product_id),
    ean = COALESCE(EXCLUDED.ean, listings.ean),
    name = EXCLUDED.name,
    brand = EXCLUDED.brand,
    brand_id = EXCLUDED.brand_id,
    url_web = EXCLUDED.url_web,
    image_url = EXCLUDED.image_url,
    category = EXCLUDED.category,
    category_path = EXCLUDED.category_path,
    envase = EXCLUDED.envase,
    measurement_unit = EXCLUDED.measurement_unit,
    unit_multiplier = EXCLUDED.unit_multiplier,
    extra = EXCLUDED.extra,
    updated_at = now()
RETURNING id;
"""

INSERT_SNAPSHOT = """
INSERT INTO price_snapshots (
    listing_id,
    scraped_at,
    currency,
    price_list,
    price_final,
    price_per_unit_list,
    price_per_unit_final,
    content_amount,
    content_unit,
    units_per_pack,
    raw
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (listing_id, scraped_at) DO NOTHING;
"""


def get_database_url() -> str | None:
    for env_var in DB_ENV_VARS:
        value = os.getenv(env_var)
        if value:
            return value.strip()
    return None


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _normalize_ean(value: Any) -> str | None:
    if value in (None, ""):
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if 8 <= len(digits) <= 14:
        return digits
    return None


def _parse_scraped_at(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        raw = value.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _jsonb(value: Any):
    if Jsonb is None:
        return value
    return Jsonb(value)


def _market_meta(market_code: str, market_url: str | None) -> dict[str, str]:
    normalized_code = (market_code or "").strip().lower() or "unknown"
    fallback_name = normalized_code.title() if normalized_code != "unknown" else "Unknown"
    base = MARKETS.get(normalized_code, {})
    return {
        "code": base.get("code", normalized_code),
        "name": base.get("name", fallback_name),
        "base_url": market_url or base.get("base_url", ""),
    }


def _ensure_schema(connection) -> None:
    global _schema_applied
    if _schema_applied:
        return

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    ddl = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = [statement.strip() for statement in ddl.split(";") if statement.strip()]

    for statement in statements:
        connection.execute(statement)

    _schema_applied = True


def _build_source_product_id(product: dict[str, Any]) -> str:
    candidates = (
        product.get("productReference"),
        product.get("itemId"),
        product.get("productId"),
        product.get("ean"),
        product.get("link"),
        product.get("name"),
    )

    for value in candidates:
        if value not in (None, ""):
            return str(value)

    payload = json.dumps(product, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"fallback:{digest}"


def _build_extra(product: dict[str, Any]) -> dict[str, Any]:
    known_fields = {
        "source",
        "scrapedAt",
        "name",
        "brand",
        "ean",
        "image",
        "link",
        "categoryPath",
        "category",
        "regularPrice",
        "effectivePrice",
        "regularReferencePrice",
        "effectiveReferencePrice",
        "contentAmount",
        "contentUnit",
        "unitsPerPack",
        "envase",
        "productId",
        "itemId",
        "productReference",
        "brand_id",
        "measurementUnit",
        "unitMultiplier",
        "priceValidUntil",
    }
    return {k: v for k, v in product.items() if k not in known_fields and v is not None}


def persist_market_snapshot(
    market_code: str,
    products: Iterable[dict[str, Any]],
    market_url: str | None = None,
) -> dict[str, Any]:
    product_list = list(products or [])
    result = {
        "enabled": False,
        "market": (market_code or "").lower(),
        "received": len(product_list),
        "snapshots_inserted": 0,
        "errors": 0,
    }

    db_url = get_database_url()
    if not db_url:
        result["reason"] = "missing_database_url"
        return result

    if psycopg is None:
        result["reason"] = "missing_psycopg_dependency"
        return result

    market = _market_meta(market_code, market_url)

    try:
        with psycopg.connect(db_url, autocommit=True) as connection:
            _ensure_schema(connection)

            first_error_printed = False

            with connection.cursor() as cursor:
                cursor.execute(
                    UPSERT_SUPERMARKET,
                    (market["code"], market["name"], market["base_url"]),
                )
                supermarket_id = cursor.fetchone()[0]

                for product in product_list:
                    if not isinstance(product, dict):
                        result["errors"] += 1
                        continue

                    try:
                        with connection.transaction():
                            source_product_id = _build_source_product_id(product)
                            ean = _normalize_ean(product.get("ean"))
                            name = (str(product.get("name") or "").strip() or "SIN_NOMBRE")
                            category = (str(product.get("category") or "").strip() or "sin-categoria")
                            category_path = (
                                str(product.get("categoryPath") or "").strip() or f"/{category}/"
                            )

                            product_id = None
                            if ean:
                                cursor.execute(
                                    UPSERT_PRODUCT,
                                    (
                                        ean,
                                        name,
                                        product.get("brand"),
                                        _to_decimal(product.get("contentAmount")),
                                        product.get("contentUnit"),
                                        product.get("envase"),
                                    ),
                                )
                                product_id = cursor.fetchone()[0]

                            cursor.execute(
                                UPSERT_LISTING,
                                (
                                    supermarket_id,
                                    source_product_id,
                                    product_id,
                                    ean,
                                    name,
                                    product.get("brand"),
                                    _to_int(product.get("brand_id")),
                                    product.get("link") or "",
                                    product.get("image"),
                                    category,
                                    category_path,
                                    product.get("envase"),
                                    product.get("measurementUnit") or product.get("contentUnit"),
                                    _to_decimal(product.get("unitMultiplier")),
                                    _jsonb(_build_extra(product)),
                                ),
                            )
                            listing_id = cursor.fetchone()[0]

                            cursor.execute(
                                INSERT_SNAPSHOT,
                                (
                                    listing_id,
                                    _parse_scraped_at(product.get("scrapedAt")),
                                    "ARS",
                                    _to_decimal(product.get("regularPrice")),
                                    _to_decimal(product.get("effectivePrice")),
                                    _to_decimal(product.get("regularReferencePrice")),
                                    _to_decimal(product.get("effectiveReferencePrice")),
                                    _to_decimal(product.get("contentAmount")),
                                    product.get("contentUnit"),
                                    _to_int(product.get("unitsPerPack")),
                                    _jsonb(product),
                                ),
                            )

                            if cursor.rowcount == 1:
                                result["snapshots_inserted"] += 1

                    except Exception as e:
                        if not first_error_printed:
                            print(f"First DB error for {market['code']}: {type(e).__name__}: {e}")
                            first_error_printed = True
                        result["errors"] += 1

        result["enabled"] = True
        return result

    except Exception as exc:
        result["reason"] = "db_error"
        result["error"] = str(exc)
        return result


REFRESH_LATEST_PRICES_SQL = """
    INSERT INTO latest_prices (listing_id, scraped_at, price_list, price_final, price_per_unit_list, price_per_unit_final, updated_at)
    SELECT listing_id, scraped_at, price_list, price_final, price_per_unit_list, price_per_unit_final, now()
    FROM (
        SELECT ps.listing_id, ps.scraped_at, ps.price_list, ps.price_final,
               ps.price_per_unit_list, ps.price_per_unit_final,
               ROW_NUMBER() OVER (PARTITION BY ps.listing_id ORDER BY ps.scraped_at DESC) AS rn
        FROM price_snapshots ps
        JOIN listings l ON l.id = ps.listing_id
        JOIN supermarket s ON s.id = l.supermarket_id
        WHERE s.code = %s
    ) sub
    WHERE rn = 1
    ON CONFLICT (listing_id) DO UPDATE SET
        scraped_at = EXCLUDED.scraped_at,
        price_list = EXCLUDED.price_list,
        price_final = EXCLUDED.price_final,
        price_per_unit_list = EXCLUDED.price_per_unit_list,
        price_per_unit_final = EXCLUDED.price_per_unit_final,
        updated_at = now();
"""


def refresh_latest_prices(market_code: str) -> dict[str, Any]:
    """Refresh latest_prices table for a specific market after scraping."""
    result = {"success": False, "market": market_code}

    db_url = get_database_url()
    if not db_url or psycopg is None:
        result["reason"] = "db_not_available"
        return result

    try:
        with psycopg.connect(db_url, autocommit=True) as conn:
            conn.execute(REFRESH_LATEST_PRICES_SQL, (market_code,))
            result["success"] = True
            print(f"latest_prices refreshed for {market_code}.")
    except Exception as exc:
        result["error"] = str(exc)
        print(f"Error refreshing latest_prices for {market_code}: {exc}")

    return result

import argparse
import json
import os
import sys
import time
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


VALID_MARKETS = {"carrefour", "coto", "dia"}
SCHEMA_FILE = ROOT_DIR / "data" / "schema.sql"

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

CREATE_STAGE_TABLES = """
CREATE TEMP TABLE IF NOT EXISTS _stage_raw (
    raw JSONB NOT NULL
);

CREATE TEMP TABLE IF NOT EXISTS _stage_norm (
    source_product_id TEXT NOT NULL,
    ean TEXT,
    name TEXT NOT NULL,
    brand TEXT,
    brand_id BIGINT,
    url_web TEXT NOT NULL,
    image_url TEXT,
    category TEXT NOT NULL,
    category_path TEXT NOT NULL,
    envase TEXT,
    measurement_unit TEXT,
    unit_multiplier NUMERIC,
    content_amount NUMERIC,
    content_unit TEXT,
    units_per_pack INTEGER,
    price_list NUMERIC,
    price_final NUMERIC,
    price_per_unit_list NUMERIC,
    price_per_unit_final NUMERIC,
    scraped_at TIMESTAMPTZ NOT NULL,
    raw JSONB NOT NULL
);
"""

TRUNCATE_STAGE_TABLES = "TRUNCATE TABLE _stage_raw; TRUNCATE TABLE _stage_norm;"

NORMALIZE_STAGE = r"""
INSERT INTO _stage_norm (
    source_product_id,
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
    content_amount,
    content_unit,
    units_per_pack,
    price_list,
    price_final,
    price_per_unit_list,
    price_per_unit_final,
    scraped_at,
    raw
)
SELECT
    COALESCE(
        NULLIF(raw->>'productReference', ''),
        NULLIF(raw->>'itemId', ''),
        NULLIF(raw->>'productId', ''),
        NULLIF(raw->>'ean', ''),
        NULLIF(raw->>'link', ''),
        NULLIF(raw->>'name', ''),
        'fallback:' || md5(raw::text)
    ) AS source_product_id,
    CASE
        WHEN regexp_replace(COALESCE(raw->>'ean', ''), '\\D', '', 'g') ~ '^[0-9]{8,14}$'
        THEN regexp_replace(raw->>'ean', '\\D', '', 'g')
        ELSE NULL
    END AS ean,
    COALESCE(NULLIF(raw->>'name', ''), 'SIN_NOMBRE') AS name,
    NULLIF(raw->>'brand', '') AS brand,
    CASE
        WHEN NULLIF(raw->>'brand_id', '') ~ '^-?[0-9]+$'
        THEN (raw->>'brand_id')::BIGINT
        ELSE NULL
    END AS brand_id,
    COALESCE(NULLIF(raw->>'link', ''), '') AS url_web,
    NULLIF(raw->>'image', '') AS image_url,
    COALESCE(NULLIF(raw->>'category', ''), 'sin-categoria') AS category,
    COALESCE(
        NULLIF(raw->>'categoryPath', ''),
        '/' || COALESCE(NULLIF(raw->>'category', ''), 'sin-categoria') || '/'
    ) AS category_path,
    NULLIF(raw->>'envase', '') AS envase,
    COALESCE(NULLIF(raw->>'measurementUnit', ''), NULLIF(raw->>'contentUnit', '')) AS measurement_unit,
    CASE
        WHEN replace(COALESCE(raw->>'unitMultiplier', ''), ',', '.') ~ '^-?[0-9]+(\.[0-9]+)?$'
        THEN replace(raw->>'unitMultiplier', ',', '.')::NUMERIC
        ELSE NULL
    END AS unit_multiplier,
    CASE
        WHEN replace(COALESCE(raw->>'contentAmount', ''), ',', '.') ~ '^-?[0-9]+(\.[0-9]+)?$'
        THEN replace(raw->>'contentAmount', ',', '.')::NUMERIC
        ELSE NULL
    END AS content_amount,
    NULLIF(raw->>'contentUnit', '') AS content_unit,
    CASE
        WHEN COALESCE(raw->>'unitsPerPack', '') ~ '^-?[0-9]+$'
        THEN (raw->>'unitsPerPack')::INTEGER
        ELSE NULL
    END AS units_per_pack,
    CASE
        WHEN replace(COALESCE(raw->>'regularPrice', raw->>'listPrice', ''), ',', '.') ~ '^-?[0-9]+(\.[0-9]+)?$'
        THEN replace(COALESCE(raw->>'regularPrice', raw->>'listPrice', ''), ',', '.')::NUMERIC(12,2)
        ELSE NULL
    END AS price_list,
    CASE
        WHEN replace(COALESCE(raw->>'effectivePrice', raw->>'price', raw->>'spotPrice', ''), ',', '.') ~ '^-?[0-9]+(\.[0-9]+)?$'
        THEN replace(COALESCE(raw->>'effectivePrice', raw->>'price', raw->>'spotPrice', ''), ',', '.')::NUMERIC(12,2)
        ELSE NULL
    END AS price_final,
    CASE
        WHEN replace(COALESCE(raw->>'regularReferencePrice', ''), ',', '.') ~ '^-?[0-9]+(\.[0-9]+)?$'
        THEN replace(raw->>'regularReferencePrice', ',', '.')::NUMERIC(12,4)
        ELSE NULL
    END AS price_per_unit_list,
    CASE
        WHEN replace(COALESCE(raw->>'effectiveReferencePrice', ''), ',', '.') ~ '^-?[0-9]+(\.[0-9]+)?$'
        THEN replace(raw->>'effectiveReferencePrice', ',', '.')::NUMERIC(12,4)
        ELSE NULL
    END AS price_per_unit_final,
    CASE
        WHEN COALESCE(raw->>'scrapedAt', '') ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T'
        THEN (replace(raw->>'scrapedAt', 'Z', '+00:00'))::TIMESTAMPTZ
        ELSE now()
    END AS scraped_at,
    raw
FROM _stage_raw;
"""

UPSERT_PRODUCTS = """
INSERT INTO products (ean, name, brand, content_amount, content_unit, envase, updated_at)
SELECT
    s.ean,
    s.name,
    s.brand,
    s.content_amount,
    s.content_unit,
    s.envase,
    now()
FROM (
    SELECT DISTINCT ON (ean)
        ean,
        name,
        brand,
        content_amount,
        content_unit,
        envase,
        scraped_at
    FROM _stage_norm
    WHERE ean IS NOT NULL
    ORDER BY ean, scraped_at DESC
) s
ON CONFLICT (ean)
DO UPDATE SET
    name = EXCLUDED.name,
    brand = EXCLUDED.brand,
    content_amount = COALESCE(EXCLUDED.content_amount, products.content_amount),
    content_unit = COALESCE(EXCLUDED.content_unit, products.content_unit),
    envase = COALESCE(EXCLUDED.envase, products.envase),
    updated_at = now();
"""

UPSERT_LISTINGS = """
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
SELECT
    %s AS supermarket_id,
    n.source_product_id,
    p.id AS product_id,
    n.ean,
    n.name,
    n.brand,
    n.brand_id,
    n.url_web,
    n.image_url,
    n.category,
    n.category_path,
    n.envase,
    n.measurement_unit,
    n.unit_multiplier,
    '{}'::JSONB AS extra,
    now(),
    now()
FROM (
    SELECT DISTINCT ON (source_product_id)
        source_product_id,
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
        scraped_at
    FROM _stage_norm
    ORDER BY source_product_id, scraped_at DESC
) n
LEFT JOIN products p ON p.ean = n.ean
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
    updated_at = now();
"""

INSERT_SNAPSHOTS = """
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
SELECT
    l.id,
    n.scraped_at,
    'ARS',
    CASE
        WHEN n.price_list IS NOT NULL AND abs(n.price_list) < 10000000000
        THEN round(n.price_list, 2)::NUMERIC(12,2)
        ELSE NULL
    END,
    CASE
        WHEN n.price_final IS NOT NULL AND abs(n.price_final) < 10000000000
        THEN round(n.price_final, 2)::NUMERIC(12,2)
        ELSE NULL
    END,
    CASE
        WHEN n.price_per_unit_list IS NOT NULL AND abs(n.price_per_unit_list) < 100000000
        THEN round(n.price_per_unit_list, 4)::NUMERIC(12,4)
        ELSE NULL
    END,
    CASE
        WHEN n.price_per_unit_final IS NOT NULL AND abs(n.price_per_unit_final) < 100000000
        THEN round(n.price_per_unit_final, 4)::NUMERIC(12,4)
        ELSE NULL
    END,
    CASE
        WHEN n.content_amount IS NOT NULL AND abs(n.content_amount) < 1000000000
        THEN round(n.content_amount, 3)::NUMERIC(12,3)
        ELSE NULL
    END,
    n.content_unit,
    n.units_per_pack,
    n.raw
FROM _stage_norm n
JOIN listings l
  ON l.supermarket_id = %s
 AND l.source_product_id = n.source_product_id
ON CONFLICT (listing_id, scraped_at) DO NOTHING;
"""


def get_database_url() -> str | None:
    url = (
        os.getenv("COMPARAR_DATABASE_URL")
        or os.getenv("DATABASE_URL")
    )
    if url and "?sslmode=verify-full" in url:
        url = url.replace("?sslmode=verify-full", "?sslmode=require")
    return url


def market_meta(market: str) -> tuple[str, str, str]:
    market = market.lower()
    if market == "carrefour":
        return "carrefour", "Carrefour", "https://www.carrefour.com.ar"
    if market == "dia":
        return "dia", "Dia", "https://diaonline.supermercadosdia.com.ar"
    if market == "coto":
        return "coto", "Coto", "https://www.cotodigital.com.ar"
    return market, market.title(), ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bulk import local JSON snapshots (data/results) into Neon/PostgreSQL."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/results"),
        help="Base directory that contains market folders with JSON files.",
    )
    parser.add_argument(
        "--market",
        action="append",
        default=[],
        help="Filter by market (carrefour, coto, dia). Can be repeated.",
    )
    parser.add_argument(
        "--limit-files",
        type=int,
        default=0,
        help="Process only first N files. 0 = all files.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop when a file fails.",
    )
    return parser.parse_args()


def discover_files(data_dir: Path, markets: set[str]) -> list[Path]:
    files: list[Path] = []
    for market_dir in sorted(data_dir.iterdir()):
        if not market_dir.is_dir():
            continue
        market = market_dir.name.lower()
        if market not in VALID_MARKETS:
            continue
        if markets and market not in markets:
            continue
        files.extend(sorted(market_dir.glob("*.json")))
    return files


def ensure_schema(conn) -> None:
    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_FILE}")

    required_tables = ("supermarket", "products", "listings", "price_snapshots")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT count(*)
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = ANY(%s)
            """,
            (list(required_tables),),
        )
        existing = int(cur.fetchone()[0])

    if existing == len(required_tables):
        conn.commit()
        return

    ddl = SCHEMA_FILE.read_text(encoding="utf-8")
    statements = [s.strip() for s in ddl.split(";") if s.strip()]
    with conn.cursor() as cur:
        for stmt in statements:
            try:
                cur.execute(stmt)
            except (
                psycopg.errors.DuplicateTable,
                psycopg.errors.DuplicateObject,
                psycopg.errors.UniqueViolation,
            ):
                continue
    conn.commit()


def ensure_stage_tables(conn) -> None:
    with conn.cursor() as cur:
        try:
            cur.execute("SET experimental_enable_temp_tables = 'on';")
        except:
            pass
        cur.execute(CREATE_STAGE_TABLES)
    conn.commit()


def upsert_supermarkets(conn) -> dict[str, int]:
    result: dict[str, int] = {}
    with conn.cursor() as cur:
        for market in sorted(VALID_MARKETS):
            code, name, url = market_meta(market)
            cur.execute(UPSERT_SUPERMARKET, (code, name, url))
            result[market] = int(cur.fetchone()[0])
    conn.commit()
    return result


def load_stage_raw(cur, rows: list[dict]) -> None:
    data = [(Jsonb(row),) for row in rows if isinstance(row, dict)]
    cur.executemany("INSERT INTO _stage_raw (raw) VALUES (%s)", data)


def process_file(conn, file_path: Path, supermarket_id: int) -> tuple[int, int]:
    with file_path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    if not isinstance(payload, list):
        raise ValueError(f"Expected list in {file_path.name}, got {type(payload).__name__}")

    with conn.cursor() as cur:
        cur.execute(TRUNCATE_STAGE_TABLES)
        load_stage_raw(cur, payload)
        cur.execute(NORMALIZE_STAGE)
        cur.execute(UPSERT_PRODUCTS)
        cur.execute(UPSERT_LISTINGS, (supermarket_id,))
        cur.execute(INSERT_SNAPSHOTS, (supermarket_id,))
        snapshots_inserted = cur.rowcount

    return len(payload), snapshots_inserted


def main() -> int:
    args = parse_args()

    db_url = get_database_url()
    if not db_url:
        print("ERROR: missing COMPARAR_DATABASE_URL or DATABASE_URL.")
        return 1

    if not args.data_dir.exists():
        print(f"ERROR: data dir not found: {args.data_dir}")
        return 1

    market_filters = {m.strip().lower() for m in args.market if m.strip()}
    invalid = sorted(m for m in market_filters if m not in VALID_MARKETS)
    if invalid:
        print(f"ERROR: invalid market values: {', '.join(invalid)}")
        return 1

    files = discover_files(args.data_dir, market_filters)
    if args.limit_files and args.limit_files > 0:
        files = files[: args.limit_files]

    if not files:
        print("No files to import.")
        return 0

    print(f"Importing {len(files)} file(s) into PostgreSQL...")
    started = time.time()

    totals = {
        "files_ok": 0,
        "files_failed": 0,
        "products_read": 0,
        "snapshots_inserted": 0,
    }

    conn = psycopg.connect(db_url, autocommit=False)
    try:
        ensure_schema(conn)
        ensure_stage_tables(conn)
        supermarket_ids = upsert_supermarkets(conn)

        for i, file_path in enumerate(files, start=1):
            market = file_path.parent.name.lower()
            supermarket_id = supermarket_ids[market]
            file_start = time.time()
            try:
                rows_read, inserted = process_file(conn, file_path, supermarket_id)
                conn.commit()
                elapsed = round(time.time() - file_start, 2)
                totals["files_ok"] += 1
                totals["products_read"] += rows_read
                totals["snapshots_inserted"] += inserted
                print(
                    f"[{i}/{len(files)}] OK   {file_path.name}: "
                    f"{rows_read} read, {inserted} inserted, {elapsed}s"
                )
            except Exception as exc:
                conn.rollback()
                totals["files_failed"] += 1
                print(f"[{i}/{len(files)}] FAIL {file_path.name}: {exc}")
                if args.stop_on_error:
                    break
    finally:
        conn.close()

    elapsed_total = round(time.time() - started, 2)
    print("")
    print("Import summary")
    print(f"- Files OK: {totals['files_ok']}")
    print(f"- Files failed: {totals['files_failed']}")
    print(f"- Products read: {totals['products_read']}")
    print(f"- Snapshots inserted: {totals['snapshots_inserted']}")
    print(f"- Time (s): {elapsed_total}")

    return 0 if totals["files_failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

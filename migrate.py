"""Run database migrations for latest_prices and cba_monthly tables."""
import os
import sys
import psycopg
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("COMPARAR_DATABASE_URL") or os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: Set COMPARAR_DATABASE_URL (or DATABASE_URL) before running migrations.")
    sys.exit(1)

migration_file = Path(__file__).parent / "data" / "latest_prices_migration.sql"
sql = migration_file.read_text(encoding="utf-8")

print("Connecting to database...")
with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
    print("Running latest_prices migration...")
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement:
            conn.execute(statement)

    # Populate latest_prices from existing price_snapshots
    print("Populating latest_prices from existing data (this may take a minute)...")
    conn.execute("""
        INSERT INTO latest_prices (listing_id, scraped_at, price_list, price_final, price_per_unit_list, price_per_unit_final, updated_at)
        SELECT listing_id, scraped_at, price_list, price_final, price_per_unit_list, price_per_unit_final, now()
        FROM (
            SELECT listing_id, scraped_at, price_list, price_final, price_per_unit_list, price_per_unit_final,
                   ROW_NUMBER() OVER (PARTITION BY listing_id ORDER BY scraped_at DESC) AS rn
            FROM price_snapshots
        ) sub
        WHERE rn = 1
        ON CONFLICT (listing_id) DO UPDATE SET
            scraped_at = EXCLUDED.scraped_at,
            price_list = EXCLUDED.price_list,
            price_final = EXCLUDED.price_final,
            price_per_unit_list = EXCLUDED.price_per_unit_list,
            price_per_unit_final = EXCLUDED.price_per_unit_final,
            updated_at = now();
    """)
    print("Done! latest_prices populated.")

"""Run database migrations for latest_prices and cba_monthly tables."""
import psycopg
from pathlib import Path

DATABASE_URL = "postgresql://malfattigianluca:ACmDynLRB1WHkk6SGsaWEQ@smiley-bunny-22979.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=require"

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

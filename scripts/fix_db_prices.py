import psycopg
import os
from dotenv import load_dotenv

load_dotenv("H:/ComparAr/.env")
db_url = os.getenv("COMPARAR_DATABASE_URL")

try:
    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            UPDATE price_snapshots
            SET 
              price_final = (COALESCE(raw->>'regularPrice', raw->>'listPrice', raw->>'PriceWithoutDiscount', raw->>'spotPrice', raw->>'price'))::NUMERIC(12,2),
              price_list = (COALESCE(raw->>'regularPrice', raw->>'listPrice', raw->>'PriceWithoutDiscount', raw->>'spotPrice', raw->>'price'))::NUMERIC(12,2)
            WHERE raw IS NOT NULL AND raw != '{}'::jsonb;
            """)
            print("Snaps Update complete. Rows affected:", cur.rowcount)
            
            cur.execute("""
            TRUNCATE TABLE latest_prices;
            
            INSERT INTO latest_prices (listing_id, scraped_at, price_list, price_final, price_per_unit_list, price_per_unit_final, updated_at)
            SELECT listing_id, scraped_at, price_list, price_final, price_per_unit_list, price_per_unit_final, now()
            FROM (
                SELECT listing_id, scraped_at, price_list, price_final, price_per_unit_list, price_per_unit_final,
                       ROW_NUMBER() OVER(PARTITION BY listing_id ORDER BY scraped_at DESC) as rn
                FROM price_snapshots
            ) sub
            WHERE sub.rn = 1;
            """)
            print("Latest prices recomputed.")
            
except Exception as e:
    print(f"Error: {e}")

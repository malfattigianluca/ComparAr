import psycopg
import os
from dotenv import load_dotenv

load_dotenv("H:/ComparAr/.env")
db_url = os.getenv("COMPARAR_DATABASE_URL")

try:
    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            # 1. Faster delete using source_product_id logic or limit
            print("Detecting Dia IDs with Coto format...")
            
            # Coto source_product_id format is like '00011464-00011464-200' 
            # Dia source_product_id format is EAN (numeric mostly, 8-14 chars)
            cur.execute("""
                WITH bad_listings AS (
                    SELECT l.id FROM listings l
                    WHERE l.supermarket_id = (SELECT id FROM supermarket WHERE code = 'dia')
                    AND l.url_web LIKE '%%cotodigital%%'
                )
                DELETE FROM price_snapshots ps
                USING bad_listings bl
                WHERE ps.listing_id = bl.id;
            """)
            print(f"Deleted {cur.rowcount} corrupted price_snapshots")
            
            cur.execute("""
                WITH bad_listings AS (
                    SELECT l.id FROM listings l
                    WHERE l.supermarket_id = (SELECT id FROM supermarket WHERE code = 'dia')
                    AND l.url_web LIKE '%%cotodigital%%'
                )
                DELETE FROM latest_prices lp
                USING bad_listings bl
                WHERE lp.listing_id = bl.id;
            """)
            print(f"Deleted {cur.rowcount} corrupted latest_prices")
            
            cur.execute("""
                DELETE FROM listings l
                WHERE l.supermarket_id = (SELECT id FROM supermarket WHERE code = 'dia')
                AND l.url_web LIKE '%%cotodigital%%'
            """)
            print(f"Deleted {cur.rowcount} corrupted listings")

            # 2. Fix Coto image URLs
            cur.execute("""
                UPDATE listings
                SET image_url = 'https://static.cotodigital3.com.ar' || image_url
                WHERE supermarket_id = (SELECT id FROM supermarket WHERE code = 'coto')
                AND image_url LIKE '/sitios/%%'
            """)
            print(f"Updated {cur.rowcount} Coto relative images in listings")

except Exception as e:
    print(f"DB Error: {e}")

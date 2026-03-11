import psycopg
import os
from dotenv import load_dotenv

load_dotenv("H:/ComparAr/.env")
db_url = os.getenv("COMPARAR_DATABASE_URL")

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # Check Dia products with coto URL
            cur.execute("""
                SELECT l.id, l.name, l.url_web, l.image_url, s.code
                FROM listings l
                JOIN supermarket s ON s.id = l.supermarket_id
                WHERE s.code = 'dia' AND l.url_web LIKE '%coto%'
                LIMIT 5
            """)
            print("\n--- Dia products with Coto URLs ---\n", cur.fetchall())

            # Check general Dia URLs
            cur.execute("""
                SELECT l.url_web, l.image_url
                FROM listings l
                JOIN supermarket s ON s.id = l.supermarket_id
                WHERE s.code = 'dia' AND l.image_url IS NOT NULL
                LIMIT 5
            """)
            print("\n--- Dia URLs ---\n", cur.fetchall())
            
            # Check general Coto URLs to see if they are relative
            cur.execute("""
                SELECT l.url_web, l.image_url
                FROM listings l
                JOIN supermarket s ON s.id = l.supermarket_id
                WHERE s.code = 'coto' AND l.image_url IS NOT NULL
                LIMIT 5
            """)
            print("\n--- Coto URLs ---\n", cur.fetchall())

except Exception as e:
    print(f"DB Error: {e}")

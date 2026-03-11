import psycopg
import os
from dotenv import load_dotenv

load_dotenv("H:/ComparAr/.env")
db_url = os.getenv("COMPARAR_DATABASE_URL")

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT name, supermarket_id, image_url 
            FROM listings 
            WHERE name ILIKE '%Cerveza blanca Quilmes sin alcohol%' OR name ILIKE '%Cerveza rubia clásica Quilmes 340 ml%';
            """)
            for row in cur.fetchall():
                print(row)
except Exception as e:
    print(f"Error: {e}")

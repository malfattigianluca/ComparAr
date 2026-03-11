import psycopg
import os
from dotenv import load_dotenv

load_dotenv("H:/ComparAr/.env")
db_url = os.getenv("COMPARAR_DATABASE_URL")

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT l.id, l.name, l.url_web, l.image_url, s.code
                FROM listings l
                JOIN supermarket s ON s.id = l.supermarket_id
                WHERE s.code = 'dia' AND l.url_web LIKE '%cotodigital%'
                LIMIT 5
            """)
            print("Dia listings with true Coto links:", cur.fetchall())
except Exception as e:
    print(e)

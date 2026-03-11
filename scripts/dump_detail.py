import psycopg
import os
from dotenv import load_dotenv

load_dotenv("H:/ComparAr/.env")
db_url = os.getenv("COMPARAR_DATABASE_URL")

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT l.id, l.name, l.url_web, l.image_url, s.code, l.source_product_id, l.ean
                FROM listings l
                JOIN supermarket s ON s.id = l.supermarket_id
                WHERE s.code = 'dia' AND l.url_web LIKE '%coto%'
                LIMIT 1
            """)
            dia_coto = cur.fetchone()
            print("Dia misbehaving listing:", dia_coto)
            
            if dia_coto:
                ean = dia_coto[6]
                cur.execute("""
                    SELECT l.id, l.name, l.url_web, l.image_url, s.code, l.source_product_id, l.ean
                    FROM listings l
                    JOIN supermarket s ON s.id = l.supermarket_id
                    WHERE l.ean = %s
                """, (ean,))
                print(f"All listings for EAN {ean}:\n", cur.fetchall())

except Exception as e:
    print(f"DB Error: {e}")

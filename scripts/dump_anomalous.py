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
                WHERE l.id = 1155911916473745409
            """)
            row = cur.fetchone()
            print("Anomalous listing:")
            print(f"ID: {row[0]}")
            print(f"Name: {row[1]}")
            print(f"URL: {row[2]}")
            print(f"Image: {row[3]}")
            print(f"Code: {row[4]}")
            print(f"Source ID: {row[5]}")
            print(f"EAN: {row[6]}")
except Exception as e:
    print(e)

import psycopg
import os
from dotenv import load_dotenv

load_dotenv("H:/ComparAr/.env")
db_url = os.getenv("COMPARAR_DATABASE_URL")

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, code FROM supermarket;")
            print("Supermarkets:", cur.fetchall())
except Exception as e:
    print(f"DB Error: {e}")

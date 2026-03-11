import psycopg
import os
import json
from dotenv import load_dotenv

load_dotenv("H:/ComparAr/.env")
db_url = os.getenv("COMPARAR_DATABASE_URL")

try:
    results = []
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT l.id, l.name, l.image_url, s.code 
            FROM listings l
            JOIN supermarket s ON s.id = l.supermarket_id
            WHERE l.name ILIKE '%Cerveza blanca Quilmes sin alcohol%' OR l.name ILIKE '%Cerveza rubia clásica Quilmes 340 ml%' OR l.name ILIKE '%Cerveza negra Quilmes Stout%';
            """)
            for row in cur.fetchall():
                results.append({"id": row[0], "name": row[1], "image_url": row[2], "market": row[3]})
                
    with open("H:/ComparAr/images_test.json", "w") as f:
        json.dump(results, f, indent=2)
            
except Exception as e:
    print(f"Error: {e}")

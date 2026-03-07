import psycopg
import json

url = "postgresql://malfattigianluca:ACmDynLRB1WHkk6SGsaWEQ@smiley-bunny-22979.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=require"

try:
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT raw FROM price_snapshots WHERE listing_id IN (SELECT id FROM listings WHERE supermarket_id = (SELECT id FROM supermarket WHERE name='Carrefour')) LIMIT 1;")
            row = cur.fetchone()
            if row:
                print(json.dumps(row[0], indent=2))
            else:
                print("No rows found")
except Exception as e:
    print(f"Error: {e}")

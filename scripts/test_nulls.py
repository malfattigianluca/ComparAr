import psycopg
import json

url = "postgresql://malfattigianluca:ACmDynLRB1WHkk6SGsaWEQ@smiley-bunny-22979.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=require"

try:
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT raw->>'effectivePrice', raw->>'price', raw->>'spotPrice', raw->>'regularPrice', raw->>'listPrice'
            FROM price_snapshots WHERE price_final IS NULL LIMIT 10;
            """)
            print(cur.fetchall())
except Exception as e:
    print(f"Error: {e}")

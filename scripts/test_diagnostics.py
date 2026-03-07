import psycopg
import urllib.request
import json

url = "postgresql://malfattigianluca:ACmDynLRB1WHkk6SGsaWEQ@smiley-bunny-22979.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=require"

try:
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_tsvector('spanish', 'repasador'), to_tsvector('spanish', 'asado');")
            print("Stemming check:", cur.fetchone())
            
            # Find a product with history
            cur.execute("SELECT listing_id, count(*) FROM price_snapshots GROUP BY listing_id ORDER BY count(*) DESC LIMIT 1;")
            listing_id, count = cur.fetchone()
            print(f"Listing {listing_id} has {count} snapshots.")
            
            # Fetch its history via API
            try:
                res = urllib.request.urlopen(f'http://localhost:8000/products/{listing_id}/history').read().decode()
                print("API response:", res[:200])
            except Exception as e:
                print("API error:", e)
except Exception as e:
    print(f"Error: {e}")

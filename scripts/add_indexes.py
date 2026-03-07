import os
import psycopg

url = "postgresql://malfattigianluca:ACmDynLRB1WHkk6SGsaWEQ@smiley-bunny-22979.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=require"

try:
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            print("Creating index for EAN...")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_listings_ean ON listings (ean);")
            print("Creating index for supermarket_id...")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_listings_supermarket ON listings (supermarket_id);")
            print("Creating index for name...")
            # Using trigram index if possible, otherwise skip or do GIN.
            # In CockroachDB, we can just index the name for now.
            try:
                cur.execute("CREATE INDEX IF NOT EXISTS idx_listings_name_trgm ON listings USING GIN (name gin_trgm_ops);")
            except psycopg.errors.UndefinedObject:
                print("pg_trgm extension might not be available, skipping trigram index.")
            
            print("Indexes created successfully!")
except Exception as e:
    print(f"Error: {e}")

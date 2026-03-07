import psycopg

url = "postgresql://malfattigianluca:ACmDynLRB1WHkk6SGsaWEQ@smiley-bunny-22979.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=require"

try:
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM price_snapshots WHERE price_final IS NULL AND (raw->>'price' IS NOT NULL OR raw->>'spotPrice' IS NOT NULL);")
            total = cur.fetchone()[0]
            print(f"Total rows to update: {total}")
            
            updated = 0
            batch_size = 10000
            
            while updated < total:
                cur.execute(f"""
                UPDATE price_snapshots
                SET 
                  price_final = (COALESCE(raw->>'effectivePrice', raw->>'price', raw->>'spotPrice'))::NUMERIC(12,2),
                  price_list = (COALESCE(raw->>'regularPrice', raw->>'listPrice'))::NUMERIC(12,2)
                WHERE listing_id IN (
                    SELECT listing_id FROM price_snapshots 
                    WHERE price_final IS NULL AND (raw->>'price' IS NOT NULL OR raw->>'spotPrice' IS NOT NULL)
                    LIMIT {batch_size}
                ) 
                AND scraped_at IN (
                    SELECT scraped_at FROM price_snapshots 
                    WHERE price_final IS NULL AND (raw->>'price' IS NOT NULL OR raw->>'spotPrice' IS NOT NULL)
                    LIMIT {batch_size}
                )
                AND price_final IS NULL;
                """)
                affected = cur.rowcount
                if affected == 0:
                    break
                updated += affected
                print(f"Updated {updated}/{total} rows...")
            print("Done")
except Exception as e:
    print(f"Error: {e}")

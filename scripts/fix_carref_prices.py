import psycopg

url = "postgresql://malfattigianluca:ACmDynLRB1WHkk6SGsaWEQ@smiley-bunny-22979.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=require"

try:
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            UPDATE price_snapshots
            SET 
              price_final = (COALESCE(raw->>'effectivePrice', raw->>'price', raw->>'spotPrice'))::NUMERIC(12,2),
              price_list = (COALESCE(raw->>'regularPrice', raw->>'listPrice'))::NUMERIC(12,2)
            WHERE price_final IS NULL AND (raw->>'price' IS NOT NULL OR raw->>'spotPrice' IS NOT NULL OR raw->>'effectivePrice' IS NOT NULL);
            """)
            print("Update complete. Rows affected:", cur.rowcount)
            
            cur.execute("SELECT count(*) FROM price_snapshots WHERE price_final IS NULL;")
            print("Remaining NULLs:", cur.fetchone()[0])
            
except Exception as e:
    print(f"Error: {e}")

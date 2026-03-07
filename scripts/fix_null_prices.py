import psycopg

url = "postgresql://malfattigianluca:ACmDynLRB1WHkk6SGsaWEQ@smiley-bunny-22979.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=require"

try:
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            # Check how many need updating
            cur.execute("SELECT count(*) FROM price_snapshots WHERE price_final IS NULL;")
            print("Null prices before update:", cur.fetchone()[0])
            
            print("Updating...")
            cur.execute("""
            UPDATE price_snapshots
            SET 
              price_final = 
                CASE
                    WHEN replace(COALESCE(raw->>'effectivePrice', raw->>'price', raw->>'spotPrice', ''), ',', '.') ~ '^-?[0-9]+(\.[0-9]+)?$'
                    THEN replace(COALESCE(raw->>'effectivePrice', raw->>'price', raw->>'spotPrice', ''), ',', '.')::NUMERIC(12,2)
                    ELSE NULL
                END,
              price_list = 
                CASE
                    WHEN replace(COALESCE(raw->>'regularPrice', raw->>'listPrice', ''), ',', '.') ~ '^-?[0-9]+(\.[0-9]+)?$'
                    THEN replace(COALESCE(raw->>'regularPrice', raw->>'listPrice', ''), ',', '.')::NUMERIC(12,2)
                    ELSE NULL
                END
            WHERE price_final IS NULL;
            """)
            print("Update complete. Rows affected:", cur.rowcount)
            
            cur.execute("SELECT count(*) FROM price_snapshots WHERE price_final IS NULL;")
            print("Null prices after update:", cur.fetchone()[0])
            
except Exception as e:
    print(f"Error: {e}")

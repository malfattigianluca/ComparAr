import psycopg

url = "postgresql://malfattigianluca:ACmDynLRB1WHkk6SGsaWEQ@smiley-bunny-22979.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=require"

try:
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT raw->>'price',
            CASE
                WHEN replace(COALESCE(raw->>'effectivePrice', raw->>'price', raw->>'spotPrice', ''), ',', '.') ~ '^-?[0-9]+(\\.[0-9]+)?$'
                THEN replace(COALESCE(raw->>'effectivePrice', raw->>'price', raw->>'spotPrice', ''), ',', '.')::NUMERIC(12,2)
                ELSE NULL
            END
            FROM price_snapshots WHERE price_final IS NULL LIMIT 10;
            """)
            print(cur.fetchall())
except Exception as e:
    print(f"Error: {e}")

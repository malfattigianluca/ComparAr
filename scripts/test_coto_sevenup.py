import psycopg

url = "postgresql://malfattigianluca:ACmDynLRB1WHkk6SGsaWEQ@smiley-bunny-22979.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=require"

try:
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT l.name, ps.raw, ps.price_final 
            FROM listings l 
            JOIN price_snapshots ps ON ps.listing_id = l.id 
            WHERE l.name ILIKE '%SEVEN UP%' 
            AND l.supermarket_id IN (SELECT id FROM supermarket WHERE code='coto')
            LIMIT 5;
            """)
            for row in cur.fetchall():
                print(row[0])
                print(row[1])
                print(row[2])
                print("-" * 40)
except Exception as e:
    print(f"Error: {e}")

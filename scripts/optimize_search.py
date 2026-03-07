import psycopg

url = "postgresql://malfattigianluca:ACmDynLRB1WHkk6SGsaWEQ@smiley-bunny-22979.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=require"

try:
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            EXPLAIN
            SELECT 
                l.id
            FROM listings l
            WHERE (to_tsvector('simple', coalesce(l.name, '')) @@ plainto_tsquery('simple', 'coca') OR l.ean = 'coca')
            LIMIT 100;
            """)
            print("Before Computed Column/Index EXPLAIN:")
            for row in cur.fetchall():
                print(row)
                
            print("\nAdding computed column and inverted index...")
            try:
                cur.execute("ALTER TABLE listings ADD COLUMN search_vector tsvector AS (to_tsvector('simple', coalesce(name, ''))) STORED;")
                cur.execute("CREATE INVERTED INDEX idx_listings_search_vector ON listings (search_vector);")
                print("Index created.")
            except Exception as e:
                print("Error creating index:", e)
            
            cur.execute("""
            EXPLAIN
            SELECT 
                l.id
            FROM listings l
            WHERE (search_vector @@ plainto_tsquery('simple', 'coca') OR l.ean = 'coca')
            LIMIT 100;
            """)
            print("\nAfter Computed Column/Index EXPLAIN:")
            for row in cur.fetchall():
                print(row)

except Exception as e:
    print(f"Error: {e}")

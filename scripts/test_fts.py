import psycopg

url = "postgresql://malfattigianluca:ACmDynLRB1WHkk6SGsaWEQ@smiley-bunny-22979.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=require"

try:
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM listings WHERE to_tsvector('spanish', name) @@ plainto_tsquery('spanish', 'asado') LIMIT 5;")
            print("Full text search results:", cur.fetchall())
except Exception as e:
    print(f"Error: {e}")

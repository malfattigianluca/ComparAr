import psycopg
url = "postgresql://malfattigianluca:ACmDynLRB1WHkk6SGsaWEQ@smiley-bunny-22979.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=require"
try:
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_tsvector('spanish', 'Coco Rallado') @@ plainto_tsquery('spanish', 'coca');")
            print("Spanish stemmer:", cur.fetchone()[0])
            cur.execute("SELECT to_tsvector('simple', 'Coco Rallado') @@ plainto_tsquery('simple', 'coca');")
            print("Simple stemmer:", cur.fetchone()[0])
            cur.execute("SELECT category, COUNT(*) FROM listings GROUP BY category ORDER BY COUNT(*) DESC LIMIT 20;")
            print("Categories:")
            for r in cur.fetchall():
                print(r)
except Exception as e:
    print(f"Error: {e}")

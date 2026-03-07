import psycopg
import json

url = "postgresql://malfattigianluca:ACmDynLRB1WHkk6SGsaWEQ@smiley-bunny-22979.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=require"

try:
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT '3690.0' ~ '^-?[0-9]+(\.[0-9]+)?$';
            """)
            print(cur.fetchall())
except Exception as e:
    print(f"Error: {e}")

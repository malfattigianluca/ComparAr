import os
import psycopg

url = "postgresql://malfattigianluca:ACmDynLRB1WHkk6SGsaWEQ@smiley-bunny-22979.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=require"

try:
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SET experimental_enable_temp_tables = 'on';")
            cur.execute("""
            CREATE TEMP TABLE IF NOT EXISTS _stage_raw (
                raw JSONB NOT NULL
            );
            """)
            print("Temp table created successfully!")
except Exception as e:
    print(f"Error: {e}")

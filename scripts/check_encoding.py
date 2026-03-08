import psycopg

conn = psycopg.connect('postgresql://malfattigianluca:ACmDynLRB1WHkk6SGsaWEQ@smiley-bunny-22979.j77.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=require')

# Check for mojibake (Ã pattern)
r = conn.execute("""
    SELECT l.name, s.code FROM listings l 
    JOIN supermarket s ON s.id = l.supermarket_id
    WHERE l.name LIKE '%Ã%'
    LIMIT 10
""").fetchall()
print("=== MOJIBAKE (Ã) ===")
for row in r:
    print(f'{row[1]:10} | {repr(row[0][:70])}')

# Count total affected
r3 = conn.execute("""SELECT count(*) FROM listings WHERE name LIKE '%Ã%'""").fetchone()
print(f"\nMojibake count: {r3[0]} listings")

# Check sample from API results
r5 = conn.execute("""
    SELECT l.name, s.code FROM listings l
    JOIN supermarket s ON s.id = l.supermarket_id
    WHERE l.name LIKE '%cappuccino%' OR l.name LIKE '%Cappu%' OR l.name LIKE '%caf%'
    LIMIT 10
""").fetchall()
print("\n=== CAFE/CAPPUCCINO SAMPLES ===")
for row in r5:
    print(f'{row[1]:10} | {repr(row[0][:70])}')

conn.close()

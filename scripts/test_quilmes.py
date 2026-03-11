import psycopg
import os
import json
from dotenv import load_dotenv

load_dotenv("H:/ComparAr/.env")
db_url = os.getenv("COMPARAR_DATABASE_URL")

def inspect_beer():
    ean = "7792798014835"
    out = {}
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT l.id, s.code, l.name, l.url_web
                FROM listings l
                JOIN supermarket s ON s.id = l.supermarket_id
                WHERE l.ean = %s
            """, (ean,))
            out['listings'] = [{"id": r[0], "market": r[1], "name": r[2]} for r in cursor.fetchall()]

            cursor.execute("""
                SELECT s.code, lp.price_list, lp.price_final, CAST(lp.updated_at AS TEXT), CAST(lp.scraped_at AS TEXT)
                FROM latest_prices lp
                JOIN listings l ON l.id = lp.listing_id
                JOIN supermarket s ON s.id = l.supermarket_id
                WHERE l.ean = %s
            """, (ean,))
            out['latest'] = [{"market": r[0], "list": float(r[1]) if r[1] else None, "final": float(r[2]) if r[2] else None, "updated": r[3], "scraped": r[4]} for r in cursor.fetchall()]

            cursor.execute("""
                SELECT s.code, CAST(ps.scraped_at AS TEXT), ps.price_list, ps.price_final, ps.raw
                FROM price_snapshots ps
                JOIN listings l ON l.id = ps.listing_id
                JOIN supermarket s ON s.id = l.supermarket_id
                WHERE l.ean = %s
                ORDER BY ps.scraped_at DESC
                LIMIT 30
            """, (ean,))
            out['snaps'] = [{"market": r[0], "scraped": r[1], "list": float(r[2]) if r[2] else None, "final": float(r[3]) if r[3] else None, "raw": r[4]} for r in cursor.fetchall()]
            
    with open("H:/ComparAr/quilmes_debug.json", "w") as f:
        json.dump(out, f, indent=2)

if __name__ == "__main__":
    inspect_beer()

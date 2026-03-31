"""
Backfill cba_monthly from existing price_snapshots data.
Delegates to data/cba.py which centralizes the CBA logic and item definitions.

Usage:
    COMPARAR_DATABASE_URL=<url> python scripts/backfill_cba.py
"""
import sys
import os

# Add project root to path so data/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.cba import CBA_ITEMS, calculate_cba_for_month  # noqa: F401 (re-exported for compatibility)

import psycopg

db_url = os.getenv("COMPARAR_DATABASE_URL") or os.getenv("DATABASE_URL")
if not db_url:
    print("Error: set COMPARAR_DATABASE_URL or DATABASE_URL before running.")
    sys.exit(1)

DATABASE_URL = db_url

# INDEC CBA definition for the "adulto equivalente"
# Format: (name, search_keywords, monthly_kg_or_liters, reference_unit)
# reference_unit: "kg" means we need price_per_kg, "lt" means price_per_liter, "unit" means price per unit
# NOTE: CBA_ITEMS is now defined in data/cba.py — imported above.
CBA_ITEMS = [
    # Cereales y derivados
    ("Pan",                "pan francés OR pan blanco",     6.060, "kg"),
    ("Galletitas saladas", "galletitas crackers",           0.420, "kg"),
    ("Galletitas dulces",  "galletitas dulces",             0.720, "kg"),
    ("Arroz",              "arroz largo fino",              1.260, "kg"),
    ("Harina de trigo",    "harina trigo 000",              1.020, "kg"),
    ("Fideos secos",       "fideos secos",                  1.740, "kg"),
    # Carnes
    ("Asado",              "asado tira OR asado novillo",   0.860, "kg"),
    ("Carnaza",            "carnaza OR nalga OR paleta",    1.300, "kg"),
    ("Carne picada",       "carne picada",                  1.000, "kg"),
    ("Pollo entero",       "pollo entero",                  1.940, "kg"),
    # Lacteos y huevos
    ("Leche entera",       "leche entera sachet",           9.240, "lt"),
    ("Queso cremoso",      "queso cremoso",                 0.327, "kg"),
    ("Queso de rallar",    "queso rallado OR queso sardo",  0.048, "kg"),
    ("Manteca",            "manteca",                       0.090, "kg"),
    ("Yogur",              "yogur",                         0.858, "lt"),
    ("Huevos",             "huevos",                        1.380, "kg"),  # ~23 huevos = 1.38kg
    # Frutas
    ("Naranja",            "naranja",                       2.340, "kg"),
    ("Banana",             "banana",                        1.440, "kg"),
    ("Manzana",            "manzana",                       2.280, "kg"),
    # Verduras
    ("Papa",               "papa",                          6.690, "kg"),
    ("Cebolla",            "cebolla",                       1.200, "kg"),
    ("Lechuga",            "lechuga",                       0.570, "kg"),
    ("Tomate",             "tomate redondo OR tomate perita", 2.100, "kg"),
    ("Zanahoria",          "zanahoria",                     0.690, "kg"),
    ("Zapallo",            "zapallo",                       1.440, "kg"),
    ("Batata",             "batata",                        0.690, "kg"),
    # Otros
    ("Azúcar",             "azucar",                        1.440, "kg"),
    ("Mermelada",          "mermelada",                     0.060, "kg"),
    ("Aceite girasol",     "aceite girasol",                1.200, "lt"),
    ("Sal fina",           "sal fina",                      0.150, "kg"),
    ("Vinagre",            "vinagre",                       0.090, "lt"),
    ("Café",               "cafe molido",                   0.060, "kg"),
    ("Té",                 "te en saquitos",                0.060, "kg"),
    ("Yerba mate",         "yerba mate",                    0.600, "kg"),
]


def find_cheapest_per_unit(conn, sm_id, month, search_term, unit):
    """
    Find the cheapest price_per_unit (per kg or per liter) for a search term.
    Uses price_per_unit_final if available, otherwise calculates from price_final.
    """
    # First try: use price_per_unit_final directly
    result = conn.execute("""
        SELECT MIN(lp.price_per_unit_final) as min_ppu
        FROM latest_prices lp
        JOIN listings l ON l.id = lp.listing_id
        WHERE l.supermarket_id = %s
          AND l.search_vector @@ plainto_tsquery('simple', %s)
          AND lp.price_per_unit_final IS NOT NULL
          AND lp.price_per_unit_final > 0
          AND date_trunc('month', lp.scraped_at) = %s
    """, (sm_id, search_term.split(" OR ")[0], month)).fetchone()
    
    if result and result[0]:
        return float(result[0])
    
    # Fallback: get cheapest price_final and divide by content amount
    result = conn.execute("""
        SELECT MIN(ps.price_final) as min_price
        FROM price_snapshots ps
        JOIN listings l ON l.id = ps.listing_id
        WHERE l.supermarket_id = %s
          AND date_trunc('month', ps.scraped_at) = %s
          AND l.search_vector @@ plainto_tsquery('simple', %s)
          AND ps.price_final IS NOT NULL
          AND ps.price_final > 0
    """, (sm_id, month, search_term.split(" OR ")[0])).fetchone()
    
    if result and result[0]:
        # Rough estimate: assume typical package is 1 kg/lt
        return float(result[0])
    
    return None


print("Connecting...")
with psycopg.connect(db_url, autocommit=True) as conn:
    # Clear old CBA data
    conn.execute("DELETE FROM cba_monthly WHERE 1=1")
    print("Cleared old CBA data")
    
    # Get all months with data
    rows = conn.execute("""
        SELECT DISTINCT date_trunc('month', scraped_at)::DATE as month
        FROM price_snapshots
        ORDER BY month
    """).fetchall()
    
    months = [r[0] for r in rows]
    print(f"Found {len(months)} months of data")

    sms = conn.execute("SELECT id, code FROM supermarket").fetchall()
    
    for month in months:
        for sm_id, sm_code in sms:
            total_cost = 0.0
            items_found = 0
            
            for cat_name, search_keywords, qty_per_month, ref_unit in CBA_ITEMS:
                # Try each keyword option (split by OR)
                keywords = [k.strip() for k in search_keywords.split(" OR ")]
                price_per_unit = None
                
                for kw in keywords:
                    price_per_unit = find_cheapest_per_unit(conn, sm_id, month, kw, ref_unit)
                    if price_per_unit:
                        break
                
                if price_per_unit:
                    item_cost = price_per_unit * qty_per_month
                    total_cost += item_cost
                    items_found += 1
            
            if items_found > 0:
                conn.execute("""
                    INSERT INTO cba_monthly (month, supermarket_code, total_cost, items_found)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (month, supermarket_code) DO UPDATE SET
                        total_cost = EXCLUDED.total_cost,
                        items_found = EXCLUDED.items_found,
                        calculated_at = now()
                """, (month, sm_code, round(total_cost, 2), items_found))
                print(f"  {month} | {sm_code}: ${total_cost:,.2f} ({items_found}/{len(CBA_ITEMS)} items)")

    print("\nCBA backfill complete!")

"""
Calcula la Canasta Básica Alimentaria (CBA) mensual por supermercado
y la persiste en la tabla `cba_monthly`.

Basado en la definición INDEC para el adulto equivalente (varón 30-60 años).
Cantidades en kg/litros/unidades mensuales según INDEC.
"""
import os
import sys

# ---------------------------------------------------------------------------
# Definición INDEC de la CBA
# ---------------------------------------------------------------------------

# (nombre, keyword de búsqueda, cantidad mensual, unidad de referencia)
CBA_ITEMS = [
    # Cereales y derivados
    ("Pan",                "pan francés OR pan blanco",      6.060, "kg"),
    ("Galletitas saladas", "galletitas crackers",            0.420, "kg"),
    ("Galletitas dulces",  "galletitas dulces",              0.720, "kg"),
    ("Arroz",              "arroz largo fino",               1.260, "kg"),
    ("Harina de trigo",    "harina trigo 000",               1.020, "kg"),
    ("Fideos secos",       "fideos secos",                   1.740, "kg"),
    # Carnes
    ("Asado",              "asado tira OR asado novillo",    0.860, "kg"),
    ("Carnaza",            "carnaza OR nalga OR paleta",     1.300, "kg"),
    ("Carne picada",       "carne picada",                   1.000, "kg"),
    ("Pollo entero",       "pollo entero",                   1.940, "kg"),
    # Lácteos y huevos
    ("Leche entera",       "leche entera sachet",            9.240, "lt"),
    ("Queso cremoso",      "queso cremoso",                  0.327, "kg"),
    ("Queso de rallar",    "queso rallado OR queso sardo",   0.048, "kg"),
    ("Manteca",            "manteca",                        0.090, "kg"),
    ("Yogur",              "yogur",                          0.858, "lt"),
    ("Huevos",             "huevos",                         1.380, "kg"),
    # Frutas
    ("Naranja",            "naranja",                        2.340, "kg"),
    ("Banana",             "banana",                         1.440, "kg"),
    ("Manzana",            "manzana",                        2.280, "kg"),
    # Verduras
    ("Papa",               "papa",                           6.690, "kg"),
    ("Cebolla",            "cebolla",                        1.200, "kg"),
    ("Lechuga",            "lechuga",                        0.570, "kg"),
    ("Tomate",             "tomate redondo OR tomate perita",2.100, "kg"),
    ("Zanahoria",          "zanahoria",                      0.690, "kg"),
    ("Zapallo",            "zapallo",                        1.440, "kg"),
    ("Batata",             "batata",                         0.690, "kg"),
    # Otros
    ("Azúcar",             "azucar",                         1.440, "kg"),
    ("Mermelada",          "mermelada",                      0.060, "kg"),
    ("Aceite girasol",     "aceite girasol",                 1.200, "lt"),
    ("Sal fina",           "sal fina",                       0.150, "kg"),
    ("Vinagre",            "vinagre",                        0.090, "lt"),
    ("Café",               "cafe molido",                    0.060, "kg"),
    ("Té",                 "te en saquitos",                 0.060, "kg"),
    ("Yerba mate",         "yerba mate",                     0.600, "kg"),
]


# ---------------------------------------------------------------------------
# Lógica de cálculo
# ---------------------------------------------------------------------------

def _find_cheapest_per_unit(conn, sm_id, month, search_term):
    """Precio mínimo por unidad de referencia (kg/lt) para un ítem y mes dados."""
    result = conn.execute("""
        SELECT MIN(lp.price_per_unit_final) AS min_ppu
        FROM latest_prices lp
        JOIN listings l ON l.id = lp.listing_id
        WHERE l.supermarket_id = %s
          AND l.search_vector @@ plainto_tsquery('simple', %s)
          AND lp.price_per_unit_final IS NOT NULL
          AND lp.price_per_unit_final > 0
          AND date_trunc('month', lp.scraped_at) = %s
    """, (sm_id, search_term, month)).fetchone()

    if result and result[0]:
        return float(result[0])

    # Fallback: precio más barato del mes y estimar sobre precio_final
    result = conn.execute("""
        SELECT MIN(ps.price_final) AS min_price
        FROM price_snapshots ps
        JOIN listings l ON l.id = ps.listing_id
        WHERE l.supermarket_id = %s
          AND date_trunc('month', ps.scraped_at) = %s
          AND l.search_vector @@ plainto_tsquery('simple', %s)
          AND ps.price_final IS NOT NULL
          AND ps.price_final > 0
    """, (sm_id, month, search_term)).fetchone()

    if result and result[0]:
        return float(result[0])

    return None


def calculate_cba_for_month(conn, month, sm_id, sm_code):
    """Calcula e inserta el costo CBA para un mes y supermercado dados."""
    total_cost = 0.0
    items_found = 0

    for _name, keywords, qty_per_month, _unit in CBA_ITEMS:
        price_per_unit = None
        for kw in [k.strip() for k in keywords.split(" OR ")]:
            price_per_unit = _find_cheapest_per_unit(conn, sm_id, month, kw)
            if price_per_unit:
                break

        if price_per_unit:
            total_cost += price_per_unit * qty_per_month
            items_found += 1

    if items_found == 0:
        return

    conn.execute("""
        INSERT INTO cba_monthly (month, supermarket_code, total_cost, items_found)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (month, supermarket_code) DO UPDATE SET
            total_cost = EXCLUDED.total_cost,
            items_found = EXCLUDED.items_found,
            calculated_at = now()
    """, (month, sm_code, round(total_cost, 2), items_found))

    print(f"  CBA {month} | {sm_code}: ${total_cost:,.2f} ({items_found}/{len(CBA_ITEMS)} items)")


def update_cba_current_month():
    """
    Recalcula la CBA para el mes actual en todos los supermercados.
    Llamar después de cada scraping completo.
    """
    try:
        import psycopg
    except ImportError:
        print("CBA: psycopg not available, skipping.")
        return

    db_url = os.getenv("COMPARAR_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        print("CBA: no DATABASE_URL set, skipping.")
        return

    from datetime import date
    current_month = date.today().replace(day=1)

    try:
        with psycopg.connect(db_url, autocommit=True) as conn:
            sms = conn.execute("SELECT id, code FROM supermarket").fetchall()
            for sm_id, sm_code in sms:
                calculate_cba_for_month(conn, current_month, sm_id, sm_code)
    except Exception as e:
        print(f"CBA update failed: {e}")


# ---------------------------------------------------------------------------
# Standalone: backfill de todos los meses históricos
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        import psycopg
    except ImportError:
        print("Error: psycopg not installed. Run: pip install psycopg[binary]")
        sys.exit(1)

    db_url = os.getenv("COMPARAR_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: set COMPARAR_DATABASE_URL or DATABASE_URL before running.")
        sys.exit(1)

    print("Connecting...")
    with psycopg.connect(db_url, autocommit=True) as conn:
        rows = conn.execute("""
            SELECT DISTINCT date_trunc('month', scraped_at)::DATE AS month
            FROM price_snapshots
            ORDER BY month
        """).fetchall()
        months = [r[0] for r in rows]
        print(f"Found {len(months)} months of data")

        sms = conn.execute("SELECT id, code FROM supermarket").fetchall()

        for month in months:
            for sm_id, sm_code in sms:
                calculate_cba_for_month(conn, month, sm_id, sm_code)

    print("\nCBA backfill complete!")

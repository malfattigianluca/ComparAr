from fastapi import APIRouter
from copy import deepcopy
import json
import os
from api.utils.db import get_db

router = APIRouter(prefix="/cba", tags=["cba"])

# We load CBA definition if exists, else return empty
CBA_JSON_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'cba_definition.json')

def load_cba_definition():
    if os.path.exists(CBA_JSON_PATH):
        with open(CBA_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

@router.get("/history")
async def get_cba_history():
    """
    Get the historical cost of the Canasta Basica Alimentaria over time.
    Calculates the minimum cost across all supermarkets for the defined categories.
    """
    definition = load_cba_definition()
    if not definition:
        return {"error": "CBA definition not configured", "history": []}
        
    try:
        async with get_db() as conn:
            async with conn.cursor() as cur:
                # To efficiently get the cheapest item for each category/supermarket per month,
                # we'll use a dynamic strategy. For this MVP, since calculating this on the fly 
                # for 1.5M rows is heavy, we'll run a single optimized query grouping by month.
                
                # Fetch available months
                await cur.execute("SELECT DISTINCT date_trunc('month', scraped_at)::date FROM price_snapshots ORDER BY 1 ASC;")
                months = [row['date_trunc'] for row in await cur.fetchall()]
                
                history = []
                
                for month in months:
                    monthly_cba_by_supermarket = {}
                    
                    # For each category in the INDEC definition
                    for cat in definition:
                        search_term_conditions = " OR ".join([f"l.search_vector @@ plainto_tsquery('simple', '{term}')" for term in cat['search_terms']])
                        
                        # Find the cheapest item per liter/kg in each supermarket *this month*
                        await cur.execute(f"""
                            WITH RankedItems AS (
                                SELECT s.code as market, l.id, ps.price_per_unit_final as ppu,
                                       ROW_NUMBER() OVER(PARTITION BY s.code ORDER BY ps.price_per_unit_final ASC) as rn
                                FROM price_snapshots ps
                                JOIN listings l ON l.id = ps.listing_id
                                JOIN supermarket s ON s.id = l.supermarket_id
                                WHERE date_trunc('month', ps.scraped_at) = %s
                                AND ({search_term_conditions})
                                AND ps.price_per_unit_final IS NOT NULL
                            )
                            SELECT market, ppu FROM RankedItems WHERE rn = 1;
                        """, (month,))
                        
                        cheapest_in_month = await cur.fetchall()
                        
                        # Add to the running total for each supermarket
                        qty = cat.get('quantity_kg_per_month', cat.get('quantity_lt_per_month', 1))
                        
                        for row in cheapest_in_month:
                            market = row['market']
                            ppu = row['ppu']
                            if market not in monthly_cba_by_supermarket:
                                monthly_cba_by_supermarket[market] = 0
                            monthly_cba_by_supermarket[market] += float(ppu) * qty
                            
                    # Calculate the generic average or minimum CBA of all markets for this month
                    if monthly_cba_by_supermarket:
                        history.append({
                            "date": month.strftime("%Y-%m-%d"),
                            "min_cba": min(list(monthly_cba_by_supermarket.values())),
                            "by_supermarket": monthly_cba_by_supermarket
                        })

                return {
                    "status": "success",
                    "definition_count": len(definition),
                    "history": history
                }

    except Exception as e:
        print(f"Error calculating CBA: {e}")
        return {"error": str(e), "history": []}

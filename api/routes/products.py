from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from api.models.schemas import Product, Listing, PriceHistoryItem
from api.utils.db import get_db

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/search")
async def search_products(
    q: str,
    sort_by: Optional[str] = "price",
    markets: Optional[str] = None
):
    """Search listings by name or EAN across all supermarkets."""
    if not q or len(q) < 3:
        raise HTTPException(status_code=400, detail="Query must be at least 3 characters")
    
    order_clause = "ORDER BY price_final ASC NULLS LAST"
    if sort_by == "price_desc":
        order_clause = "ORDER BY price_final DESC NULLS LAST"
    elif sort_by == "price_per_unit":
        order_clause = "ORDER BY price_per_unit_final ASC NULLS LAST"
    elif sort_by == "name":
        order_clause = "ORDER BY name ASC"

    market_filter = ""
    params = [q, q]
    
    if markets:
        market_list = [m.strip().lower() for m in markets.split(",")]
        market_filter = "AND s.code = ANY(%s)"
        params.append(market_list)
    
    query = f"""
        SELECT 
            l.id, l.supermarket_id, l.source_product_id, l.product_id, l.ean,
            l.name, l.brand, l.url_web, l.image_url, l.category,
            l.measurement_unit, l.unit_multiplier, l.envase,
            s.code as supermarket_code,
            (
                SELECT price_final 
                FROM price_snapshots ps 
                WHERE ps.listing_id = l.id AND ps.price_final IS NOT NULL
                ORDER BY scraped_at DESC LIMIT 1
            ) as price_final,
            (
                SELECT price_per_unit_final 
                FROM price_snapshots ps 
                WHERE ps.listing_id = l.id AND ps.price_per_unit_final IS NOT NULL
                ORDER BY scraped_at DESC LIMIT 1
            ) as price_per_unit_final
        FROM listings l
        JOIN supermarket s ON s.id = l.supermarket_id
        WHERE (l.search_vector @@ plainto_tsquery('simple', %s) OR l.ean = %s)
        {market_filter}
        {order_clause}
        LIMIT 100
    """
    
    async with get_db() as db:
        async with db.cursor() as cursor:
            await cursor.execute(query, params)
            results = await cursor.fetchall()
            
    return results

@router.get("/{listing_id}/history")
async def get_price_history(listing_id: int):
    """Get the price history for a specific listing."""
    query = """
        SELECT scraped_at, price_final, price_list
        FROM price_snapshots
        WHERE listing_id = %s
        ORDER BY scraped_at ASC
    """
    async with get_db() as db:
        async with db.cursor() as cursor:
            await cursor.execute(query, (listing_id,))
            results = await cursor.fetchall()
            
    if not results:
        raise HTTPException(status_code=404, detail="No history found")
        
    return results

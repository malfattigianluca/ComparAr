from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from api.utils.db import get_db

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/search")
async def search_products(
    q: str,
    sort_by: Optional[str] = "price",
    markets: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(40, ge=1, le=100)
):
    """
    Search listings by name or EAN across all supermarkets.
    Deduplicates: returns only the cheapest listing per supermarket per EAN/product.
    Supports pagination with page/per_page params.
    """
    if not q or len(q) < 3:
        raise HTTPException(status_code=400, detail="Query must be at least 3 characters")
    
    order_map = {
        "price": "price_final ASC NULLS LAST",
        "price_desc": "price_final DESC NULLS LAST",
        "price_per_unit": "price_per_unit_final ASC NULLS LAST",
        "name": "name ASC",
    }
    order_clause = order_map.get(sort_by or "price", order_map["price"])

    market_filter = ""
    params: list = [q, q]
    
    if markets:
        market_list = [m.strip().lower() for m in markets.split(",")]
        market_filter = "AND s.code = ANY(%s)"
        params.append(market_list)
    
    offset = (page - 1) * per_page
    
    # Use ROW_NUMBER to keep only the cheapest listing per (ean, supermarket) combo.
    # Cast id to text to avoid JavaScript BigInt truncation issues.
    query = f"""
        WITH matched AS (
            SELECT 
                l.id::text as id, l.supermarket_id, l.source_product_id, l.product_id, l.ean,
                l.name, l.brand, l.url_web, l.image_url, l.category,
                l.measurement_unit, l.unit_multiplier, l.envase,
                s.code as supermarket_code,
                lp.price_final,
                lp.price_per_unit_final,
                ROW_NUMBER() OVER (
                    PARTITION BY COALESCE(l.ean, l.source_product_id), s.code
                    ORDER BY lp.price_final ASC NULLS LAST
                ) AS rn
            FROM listings l
            JOIN supermarket s ON s.id = l.supermarket_id
            LEFT JOIN latest_prices lp ON lp.listing_id = l.id
            WHERE (l.search_vector @@ plainto_tsquery('simple', %s) OR l.ean = %s)
            {market_filter}
        )
        SELECT id, supermarket_id, source_product_id, product_id, ean,
               name, brand, url_web, image_url, category,
               measurement_unit, unit_multiplier, envase,
               supermarket_code, price_final, price_per_unit_final
        FROM matched
        WHERE rn = 1
        ORDER BY {order_clause}
        LIMIT %s OFFSET %s
    """
    
    # Count total unique results
    count_query = f"""
        WITH matched AS (
            SELECT 
                l.id,
                ROW_NUMBER() OVER (
                    PARTITION BY COALESCE(l.ean, l.source_product_id), s.code
                    ORDER BY lp.price_final ASC NULLS LAST
                ) AS rn
            FROM listings l
            JOIN supermarket s ON s.id = l.supermarket_id
            LEFT JOIN latest_prices lp ON lp.listing_id = l.id
            WHERE (l.search_vector @@ plainto_tsquery('simple', %s) OR l.ean = %s)
            {market_filter}
        )
        SELECT count(*) FROM matched WHERE rn = 1
    """
    
    async with get_db() as db:
        async with db.cursor() as cursor:
            # Get total count
            await cursor.execute(count_query, params)
            total = (await cursor.fetchone())['count']
            
            # Get results with pagination
            await cursor.execute(query, params + [per_page, offset])
            results = await cursor.fetchall()
    
    return {
        "results": results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }

@router.get("/{listing_id}/detail")
async def get_product_detail(listing_id: str):
    """Get full product detail: product info, all market listings, and price history."""
    async with get_db() as db:
        async with db.cursor() as cursor:
            # Get the listing info
            await cursor.execute("""
                SELECT l.id::text, l.name, l.brand, l.ean, l.image_url, l.url_web,
                       l.category, l.measurement_unit, l.unit_multiplier, l.envase,
                       s.code as supermarket_code,
                       lp.price_final, lp.price_per_unit_final
                FROM listings l
                JOIN supermarket s ON s.id = l.supermarket_id
                LEFT JOIN latest_prices lp ON lp.listing_id = l.id
                WHERE l.id = %s::INT8
            """, (listing_id,))
            listing = await cursor.fetchone()
            
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            # Get all listings for the same product across markets (by EAN)
            all_listings = []
            if listing.get('ean'):
                await cursor.execute("""
                    SELECT l.id::text, l.name, l.brand, l.ean, l.image_url, l.url_web,
                           s.code as supermarket_code,
                           lp.price_final, lp.price_per_unit_final,
                           l.measurement_unit, l.unit_multiplier
                    FROM listings l
                    JOIN supermarket s ON s.id = l.supermarket_id
                    LEFT JOIN latest_prices lp ON lp.listing_id = l.id
                    WHERE l.ean = %s AND lp.price_final IS NOT NULL
                    ORDER BY lp.price_final ASC NULLS LAST
                """, (listing['ean'],))
                all_listings = await cursor.fetchall()
            
            if not all_listings:
                all_listings = [listing] if listing.get('price_final') else []
            
            # Get price history for this listing
            await cursor.execute("""
                SELECT scraped_at, price_final, price_list
                FROM price_snapshots
                WHERE listing_id = %s::INT8
                ORDER BY scraped_at ASC
            """, (listing_id,))
            history = await cursor.fetchall()
    
    return {
        "product": listing,
        "all_listings": all_listings,
        "history": history
    }

@router.get("/{listing_id}/history")
async def get_price_history(listing_id: str):
    """Get the price history for a specific listing. Accepts string ID to avoid BigInt issues."""
    query = """
        SELECT scraped_at, price_final, price_list
        FROM price_snapshots
        WHERE listing_id = %s::INT8
        ORDER BY scraped_at ASC
    """
    async with get_db() as db:
        async with db.cursor() as cursor:
            await cursor.execute(query, (listing_id,))
            results = await cursor.fetchall()
            
    if not results:
        raise HTTPException(status_code=404, detail="No history found")
        
    return results


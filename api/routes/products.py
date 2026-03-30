from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from api.utils.db import get_db
from api.models.schemas import ProductDetailResponse, PricePoint, SearchResponse

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/search", response_model=SearchResponse)
async def search_products(
    q: str,
    sort_by: Optional[str] = "price",
    markets: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(40, ge=1, le=100),
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

    # COUNT(*) OVER() obtiene el total en la misma pasada que los resultados,
    # evitando ejecutar el CTE costoso dos veces.
    query = f"""
        WITH matched AS (
            SELECT
                l.id::text AS id,
                l.supermarket_id,
                l.source_product_id,
                l.product_id,
                l.ean,
                l.name,
                l.brand,
                l.url_web,
                l.image_url,
                l.category,
                l.measurement_unit,
                l.unit_multiplier,
                l.envase,
                s.code AS supermarket_code,
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
        ),
        deduplicated AS (
            SELECT id, supermarket_id, source_product_id, product_id, ean,
                   name, brand, url_web, image_url, category,
                   measurement_unit, unit_multiplier, envase,
                   supermarket_code, price_final, price_per_unit_final
            FROM matched
            WHERE rn = 1
        )
        SELECT *, COUNT(*) OVER() AS total_count
        FROM deduplicated
        ORDER BY {order_clause}
        LIMIT %s OFFSET %s
    """

    async with get_db() as db:
        async with db.cursor() as cursor:
            await cursor.execute(query, params + [per_page, offset])
            rows = await cursor.fetchall()

    total = rows[0]["total_count"] if rows else 0
    results = [{k: v for k, v in row.items() if k != "total_count"} for row in rows]

    return {
        "results": results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    }


@router.get("/{listing_id}/detail", response_model=ProductDetailResponse)
async def get_product_detail(listing_id: str):
    """Get full product detail: product info, all market listings, and price history."""
    async with get_db() as db:
        async with db.cursor() as cursor:
            await cursor.execute(
                """
                SELECT l.id::text, l.name, l.brand, l.ean, l.image_url, l.url_web,
                       l.category, l.measurement_unit, l.unit_multiplier, l.envase,
                       s.code AS supermarket_code,
                       lp.price_final, lp.price_per_unit_final, lp.updated_at AS price_updated_at
                FROM listings l
                JOIN supermarket s ON s.id = l.supermarket_id
                LEFT JOIN latest_prices lp ON lp.listing_id = l.id
                WHERE l.id = %s::INT8
                """,
                (listing_id,),
            )
            listing = await cursor.fetchone()

            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")

            # Listings del mismo producto en todos los mercados (por EAN)
            all_listings = []
            if listing.get("ean"):
                await cursor.execute(
                    """
                    SELECT l.id::text, l.name, l.brand, l.ean, l.image_url, l.url_web,
                           s.code AS supermarket_code,
                           lp.price_final, lp.price_per_unit_final, lp.updated_at AS price_updated_at,
                           l.measurement_unit, l.unit_multiplier
                    FROM listings l
                    JOIN supermarket s ON s.id = l.supermarket_id
                    LEFT JOIN latest_prices lp ON lp.listing_id = l.id
                    WHERE l.ean = %s AND lp.price_final IS NOT NULL
                    ORDER BY lp.price_final ASC NULLS LAST
                    """,
                    (listing["ean"],),
                )
                all_listings = await cursor.fetchall()

            if not all_listings:
                all_listings = [listing] if listing.get("price_final") else []

            # Historial de precios para todos los listings — una sola query (batch)
            # en lugar de una query por listing (N+1).
            listing_ids = [lst["id"] for lst in all_listings]
            history_rows = []
            if listing_ids:
                await cursor.execute(
                    """
                    SELECT listing_id::text, supermarket_code, scraped_at, price_final, price_list
                    FROM (
                        SELECT
                            ps.listing_id,
                            s.code AS supermarket_code,
                            ps.scraped_at,
                            ps.price_final,
                            ps.price_list,
                            ROW_NUMBER() OVER (
                                PARTITION BY ps.listing_id, DATE(ps.scraped_at)
                                ORDER BY ps.scraped_at DESC
                            ) AS rn
                        FROM price_snapshots ps
                        JOIN listings l ON l.id = ps.listing_id
                        JOIN supermarket s ON s.id = l.supermarket_id
                        WHERE ps.listing_id = ANY(%s::INT8[])
                    ) t
                    WHERE rn = 1
                    ORDER BY listing_id, scraped_at ASC
                    """,
                    (listing_ids,),
                )
                history_rows = await cursor.fetchall()

    # Agrupar historial por supermarket_code
    history: dict = {}
    for row in history_rows:
        code = row["supermarket_code"]
        if code not in history:
            history[code] = []
        history[code].append({
            "scraped_at": row["scraped_at"],
            "price_final": row["price_final"],
            "price_list": row["price_list"],
        })

    return {
        "product": listing,
        "all_listings": all_listings,
        "history": history,
    }


@router.get("/{listing_id}/history", response_model=List[PricePoint])
async def get_price_history(listing_id: str):
    """Get the price history for a specific listing (daily aggregated)."""
    query = """
        SELECT scraped_at, price_final, price_list
        FROM (
            SELECT scraped_at, price_final, price_list,
                   ROW_NUMBER() OVER (
                       PARTITION BY DATE(scraped_at) ORDER BY scraped_at DESC
                   ) AS rn
            FROM price_snapshots
            WHERE listing_id = %s::INT8
        ) t
        WHERE rn = 1
        ORDER BY scraped_at ASC
    """
    async with get_db() as db:
        async with db.cursor() as cursor:
            await cursor.execute(query, (listing_id,))
            results = await cursor.fetchall()

    return results or []

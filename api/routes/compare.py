from fastapi import APIRouter, HTTPException, Body
from typing import List
from api.models.schemas import CartItemRequest, CompareResponseItem, CartItem
from api.utils.db import get_db

router = APIRouter(prefix="/compare", tags=["compare"])


@router.post("/cart", response_model=List[CompareResponseItem])
async def compare_cart(items: List[CartItemRequest] = Body(...)):
    """
    Accepts a list of EANs and quantities.
    Returns the total cost for the exact cart in each supermarket.
    Uses latest_prices for instant lookups.

    Deduplication: si hay múltiples listings para el mismo EAN en un mercado
    (distintas presentaciones), se toma la de menor precio.
    """
    if not items:
        raise HTTPException(status_code=400, detail="Cart cannot be empty")

    eans = [item.ean for item in items]
    quantities = {item.ean: item.quantity for item in items}

    # ROW_NUMBER() garantiza que tomamos UN listing por (ean, supermarket):
    # el más barato. Evita contar el mismo producto dos veces si hay duplicados.
    query = """
        SELECT supermarket_code, ean, name, url_web, image_url, price_final
        FROM (
            SELECT
                s.code AS supermarket_code,
                l.ean,
                l.name,
                l.url_web,
                l.image_url,
                lp.price_final,
                ROW_NUMBER() OVER (
                    PARTITION BY s.code, l.ean
                    ORDER BY lp.price_final ASC
                ) AS rn
            FROM listings l
            JOIN supermarket s ON s.id = l.supermarket_id
            JOIN latest_prices lp ON lp.listing_id = l.id
            WHERE l.ean = ANY(%s)
              AND lp.price_final IS NOT NULL
        ) ranked
        WHERE rn = 1
    """

    supermarkets_data: dict = {}

    async with get_db() as db:
        async with db.cursor() as cursor:
            await cursor.execute(query, (eans,))
            results = await cursor.fetchall()

            for row in results:
                sm = row["supermarket_code"]
                if sm not in supermarkets_data:
                    supermarkets_data[sm] = {
                        "supermarket": sm,
                        "total_price": 0.0,
                        "found_items_count": 0,
                        "missing_items": set(eans),
                        "items": [],
                    }

                ean = row["ean"]
                qty = quantities.get(ean, 1)
                item_total = float(row["price_final"]) * qty

                supermarkets_data[sm]["total_price"] += item_total
                supermarkets_data[sm]["found_items_count"] += 1
                supermarkets_data[sm]["missing_items"].discard(ean)
                supermarkets_data[sm]["items"].append({
                    "ean": ean,
                    "name": row["name"],
                    "url": row["url_web"],
                    "image": row["image_url"],
                    "price_unit": float(row["price_final"]),
                    "quantity": qty,
                    "price_total": item_total,
                })

    response = []
    for data in supermarkets_data.values():
        data["missing_items"] = list(data["missing_items"])
        response.append(CompareResponseItem(**data))

    return sorted(response, key=lambda x: x.total_price)

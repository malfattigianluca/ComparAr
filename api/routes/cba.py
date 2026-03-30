from fastapi import APIRouter, HTTPException
from api.utils.db import get_db
from api.models.schemas import CBAResponse

router = APIRouter(prefix="/cba", tags=["cba"])


@router.get("/history", response_model=CBAResponse)
async def get_cba_history():
    """
    Get the historical cost of the Canasta Basica Alimentaria.
    Reads from the pre-calculated cba_monthly table (1 query instead of 360+).
    """
    try:
        async with get_db() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT month, supermarket_code, total_cost, items_found
                    FROM cba_monthly
                    ORDER BY month ASC, supermarket_code ASC;
                """)
                rows = await cur.fetchall()

        if not rows:
            return {"status": "success", "history": []}

        # Agrupar por mes → calcular mínimo entre supermercados
        months_data: dict = {}
        for row in rows:
            month_str = (
                row["month"].strftime("%Y-%m-%d")
                if hasattr(row["month"], "strftime")
                else str(row["month"])
            )
            if month_str not in months_data:
                months_data[month_str] = {"by_supermarket": {}}
            months_data[month_str]["by_supermarket"][row["supermarket_code"]] = float(row["total_cost"])

        history = []
        for date, data in sorted(months_data.items()):
            costs = list(data["by_supermarket"].values())
            history.append({
                "date": date,
                "min_cba": min(costs) if costs else 0,
                "by_supermarket": data["by_supermarket"],
            })

        return {"status": "success", "history": history}

    except Exception as e:
        print(f"Error fetching CBA history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

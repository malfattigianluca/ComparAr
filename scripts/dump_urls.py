import asyncio
import os
from api.utils.db import get_db

async def main():
    async with get_db() as db:
        async with db.cursor() as cursor:
            # Query Dia products that might have Coto URLs
            await cursor.execute("""
                SELECT l.id, l.name, l.url_web, l.image_url, s.code
                FROM listings l
                JOIN supermarket s ON s.id = l.supermarket_id
                WHERE s.code = 'dia' AND l.url_web LIKE '%coto%'
                LIMIT 5
            """)
            coto_links_in_dia = await cursor.fetchall()
            print("Dia listings with Coto links:", coto_links_in_dia)

            await cursor.execute("""
                SELECT l.id, l.name, l.url_web, l.image_url, s.code
                FROM listings l
                JOIN supermarket s ON s.id = l.supermarket_id
                WHERE s.code = 'dia'
                LIMIT 5
            """)
            normal_dia = await cursor.fetchall()
            print("Normal Dia listings:", normal_dia)

            # Let's also check if Carrefour has Dia links
            await cursor.execute("""
                SELECT l.id, l.name, l.url_web, l.image_url, s.code
                FROM listings l
                JOIN supermarket s ON s.id = l.supermarket_id
                WHERE s.code = 'carrefour' AND l.url_web LIKE '%dia%'
                LIMIT 5
            """)
            dia_links_in_carrefour = await cursor.fetchall()
            print("Carrefour listings with Dia links:", dia_links_in_carrefour)

if __name__ == "__main__":
    asyncio.run(main())

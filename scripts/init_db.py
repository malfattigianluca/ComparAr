import os
import asyncio
import sys
import psycopg

# Fix for psycopg3 async on Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

DATABASE_URL = os.getenv("COMPARAR_DATABASE_URL")
if DATABASE_URL and "?sslmode=verify-full" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("?sslmode=verify-full", "?sslmode=require")

async def init_db():
    if not DATABASE_URL:
        print("Set COMPARAR_DATABASE_URL to initialize the DB.")
        return

    print("Connecting to DB to execute schema...")
    with open("data/schema.sql", "r", encoding="utf-8") as f:
        schema = f.read()

    try:
        async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                print("Executing schema...")
                await cur.execute(schema)
            await conn.commit()
            print("Schema executed successfully!")
    except Exception as e:
        print(f"Failed to execute schema: {e}")

if __name__ == "__main__":
    asyncio.run(init_db())

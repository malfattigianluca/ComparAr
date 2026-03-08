import os
from contextlib import asynccontextmanager
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("COMPARAR_DATABASE_URL") or os.getenv("DATABASE_URL")

@asynccontextmanager
async def get_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set.")
    
    conn = await psycopg.AsyncConnection.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=10,
        autocommit=True
    )
    try:
        yield conn
    finally:
        await conn.close()

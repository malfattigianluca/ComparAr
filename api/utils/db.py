import os
from contextlib import asynccontextmanager
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("COMPARAR_DATABASE_URL") or os.getenv("DATABASE_URL")

@asynccontextmanager
async def get_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set.")
    
    # We use autocommit=True for simple read queries, or we can manage transactions manually
    async with await psycopg.AsyncConnection.connect(DATABASE_URL, row_factory=dict_row) as conn:
        yield conn

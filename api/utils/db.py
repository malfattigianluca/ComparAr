import os
from contextlib import asynccontextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("COMPARAR_DATABASE_URL") or os.getenv("DATABASE_URL")

# Pool singleton por proceso. En Vercel serverless cada instancia tiene su
# propio proceso, así que el pool vive por el tiempo de vida de la instancia.
_pool: AsyncConnectionPool | None = None


async def get_pool() -> AsyncConnectionPool:
    """Retorna el pool singleton, creándolo si no existe."""
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set.")
        _pool = AsyncConnectionPool(
            DATABASE_URL,
            min_size=1,
            max_size=5,
            kwargs={"row_factory": dict_row},
            open=False,
        )
        await _pool.open()
    return _pool


async def close_pool() -> None:
    """Cierra el pool al apagar la aplicación (lifespan shutdown)."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_db():
    """Context manager que entrega una conexión del pool."""
    pool = await get_pool()
    async with pool.connection() as conn:
        yield conn

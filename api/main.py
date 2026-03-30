import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import products, compare, cba
from api.utils.db import get_pool, close_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa el connection pool al arrancar y lo cierra al detener."""
    await get_pool()
    yield
    await close_pool()


app = FastAPI(
    title="ComparAr API",
    description="API for the ComparAr supermarket price tracker and comparator",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: en producción se lee ALLOWED_ORIGINS desde la variable de entorno.
# Ejemplo Vercel: ALLOWED_ORIGINS=https://compar-ar.vercel.app
# Para desarrollo local: ALLOWED_ORIGINS=http://localhost:5173
_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
origins = [o.strip() for o in _raw_origins.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)
app.include_router(compare.router)
app.include_router(cba.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to ComparAr API", "status": "ok"}

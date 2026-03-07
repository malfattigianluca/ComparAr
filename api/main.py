from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import products, compare, cba

app = FastAPI(
    title="ComparAr API",
    description="API for the ComparAr supermarket price tracker and comparator",
    version="1.0.0"
)

# Allow CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with frontend URL
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

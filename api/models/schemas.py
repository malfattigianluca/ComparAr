from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime


# ---------------------------------------------------------------------------
# Schemas de búsqueda y listados
# ---------------------------------------------------------------------------

class ListingSearchResult(BaseModel):
    """Un listing de producto tal como lo retorna /products/search y /products/{id}/detail."""
    id: str                              # cast a text en la query (evita BigInt truncation en JS)
    ean: Optional[str] = None
    name: str
    brand: Optional[str] = None
    url_web: str
    image_url: Optional[str] = None
    category: str
    measurement_unit: Optional[str] = None
    unit_multiplier: Optional[float] = None
    envase: Optional[str] = None
    supermarket_code: str
    price_final: Optional[float] = None
    price_per_unit_final: Optional[float] = None

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    results: List[ListingSearchResult]
    total: int
    page: int
    per_page: int
    total_pages: int


# ---------------------------------------------------------------------------
# Schemas de historial de precios
# ---------------------------------------------------------------------------

class PricePoint(BaseModel):
    scraped_at: datetime
    price_final: Optional[float] = None
    price_list: Optional[float] = None

    model_config = {"from_attributes": True}


class ProductDetailListing(BaseModel):
    """Listing con campos extra que aparecen en la vista de detalle."""
    id: str
    ean: Optional[str] = None
    name: str
    brand: Optional[str] = None
    url_web: str
    image_url: Optional[str] = None
    category: str
    measurement_unit: Optional[str] = None
    unit_multiplier: Optional[float] = None
    envase: Optional[str] = None
    supermarket_code: str
    price_final: Optional[float] = None
    price_per_unit_final: Optional[float] = None
    price_updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProductDetailResponse(BaseModel):
    product: ProductDetailListing
    all_listings: List[ProductDetailListing]
    history: Dict[str, List[PricePoint]]


# ---------------------------------------------------------------------------
# Schemas de comparación de carrito
# ---------------------------------------------------------------------------

class CartItemRequest(BaseModel):
    ean: str
    quantity: int = 1


class CartItem(BaseModel):
    ean: str
    name: str
    url: str
    image: Optional[str] = None
    price_unit: float
    quantity: int
    price_total: float


class CompareResponseItem(BaseModel):
    supermarket: str
    total_price: float
    found_items_count: int
    missing_items: List[str]
    items: List[CartItem]


# ---------------------------------------------------------------------------
# Schemas de Canasta Básica Alimentaria
# ---------------------------------------------------------------------------

class CBAMonthEntry(BaseModel):
    date: str
    min_cba: float
    by_supermarket: Dict[str, float]


class CBAResponse(BaseModel):
    status: str
    history: List[CBAMonthEntry]

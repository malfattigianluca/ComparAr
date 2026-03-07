from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class Product(BaseModel):
    id: int
    ean: Optional[str]
    name: str
    brand: Optional[str]
    content_amount: Optional[float]
    content_unit: Optional[str]
    envase: Optional[str]

class Listing(BaseModel):
    id: int
    supermarket_id: int
    source_product_id: str
    product_id: Optional[int]
    ean: Optional[str]
    name: str
    brand: Optional[str]
    url_web: str
    image_url: Optional[str]
    category: str
    price_final: Optional[float]
    price_per_unit_final: Optional[float]

class PriceHistoryItem(BaseModel):
    scraped_at: datetime
    price_final: float
    price_list: Optional[float]

class DBProductSearchResult(BaseModel):
    id: int
    ean: Optional[str]
    name: str
    brand: Optional[str]
    listings: List[Listing]

class CartItemRequest(BaseModel):
    ean: str
    quantity: int = 1

class CompareResponseItem(BaseModel):
    supermarket: str
    total_price: float
    found_items_count: int
    missing_items: List[str]
    items: List[dict]

class CBAResponse(BaseModel):
    history: List[dict]

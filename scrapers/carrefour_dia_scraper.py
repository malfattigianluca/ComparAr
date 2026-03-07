from bdb import effective
from dataclasses import is_dataclass
from bs4 import BeautifulSoup
from idna import intranges_contain
import math, random, time, os, requests, json, re
from datetime import datetime, timezone
from scrapers.coto_scraper import get_attr
from utils.pricing import pick_prices
from utils.normalizador import *

start_time = time.time()
random_delay = random.uniform(2.0, 3.0)

def best_offer_from_sellers(sellers):
    best_off = None
    best_effective = None

    for s in sellers or []:
        if not s:
            continue

        off = s.get("commertialOffer") or {}
        effective_price, regular_price = pick_prices(off)
        if effective_price is None:
            continue

        aq = off.get("AvailableQuantity")
        if aq is not None:
            try:
                if float(aq) <= 0:
                    continue
            except Exception:
                pass

        if best_off is None or effective_price < best_effective:
            best_off = off
            best_effective = effective_price

    return best_off


def getCategoriesSlug (url_market, hash_value, sender, provider):
    url = f"{url_market.rstrip('/')}/_v/segment/graphql/v1"
    
    headers = {
        "Content-Type": "application/json",
        "Origin": url_market,
        "User-Agent": "Mozilla/5.0"
    }

    payload_categories = {
        "operationName": "getMenus",
        "variables": {},
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": hash_value,
                "sender": sender,
                "provider": provider
            },
            "variables": "eyJpc01vYmlsZSI6ZmFsc2V9"
        }
    }

    responseCategories = requests.post(url=url, headers=headers, json=payload_categories)

    if responseCategories.status_code != 200:
        print(f"Error {responseCategories.status_code}: {responseCategories.text}")
        return set()
    
    data = responseCategories.json()
    menus = data.get("data", {}).get("menus", [])

    categoriesSlug = set()

    if url_market == "https://diaonline.supermercadosdia.com.ar":
        for menu in menus:
            slug_root = menu.get("slug")
            if slug_root:
                if "http" in slug_root:
                    slug = slug_root.rstrip("/").split("/")[-1].split("?")[0]
                else:
                    slug = slug_root.strip("/").split("?")[0]
                categoriesSlug.add(slug)
    elif url_market == "https://www.carrefour.com.ar":
        for menu in menus:
            if "menu" in menu and isinstance(menu["menu"], list):
                for subMenu in menu["menu"]:
                    slugRoot = subMenu.get("slug")
                    if slugRoot:
                        slug = slugRoot.split("?")[0].strip("/").split("/")[0]
                        categoriesSlug.add(slug)
                    
                    if "menu" in subMenu and isinstance(subMenu["menu"], list):
                        for subsub in subMenu["menu"]:
                            sub_slug_root = subsub.get("slug")
                            if sub_slug_root:
                                slug = sub_slug_root.split("?")[0].strip("/").split("/")[0]
                                categoriesSlug.add(slug)
            else:
                slugRoot = menu.get("slug")
                if slugRoot:
                    slug = slugRoot.rstrip("/").split("?")[0].split("/")[-1]
                    categoriesSlug.add(slug)
    
    clean_categories = {
        slug
        for slug in categoriesSlug
        if slug and not slug.isdigit()
    }

    return clean_categories

def scrapeProducts(url_market, category, hash_value, sender, provider, map_value):
    market_name = "carrefour" if "carrefour" in url_market else "dia"

    '''
    # DEBUG
    stats = {
        "total_api_products": 0,
        "saved": 0,
        "no_items": 0,
        "no_sellers": 0,
        "no_offer": 0,
        "no_price": 0,
        "price_le_0": 0,
        "exceptions": 0,
        "empty_pages": 0,
        "last_page_from": None,
        "last_page_to": None,
    }'''

    from_value = 0
    to_value = 1
    url = f"{url_market.rstrip('/')}/_v/segment/graphql/v1"

    headers = {
        "Content-Type": "application/json",
        "Origin": url_market,
        "User-Agent": "Mozilla/5.0"
    }

    is_category_id = category.isdigit()

    payload_base = {
        "operationName": "productSearchV3",
        "variables": {
            "hideUnavailableItems": True,
            "skusFilter": "ALL_AVAILABLE",
            "query": "" if is_category_id else category,
            "from": from_value,
            "to": to_value,
            "selectedFacets": [
                {"key": "c", "value": category}
            ],
            "map": "c" if is_category_id else map_value,
            "orderBy": "OrderByNameASC"
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": hash_value,
                "sender": sender,
                "provider": provider
            }
        }
    }

    response_GetProducts = requests.post(url, headers=headers, json=payload_base)
    if response_GetProducts.status_code != 200:
        print(f"{category} - Error {response_GetProducts.status_code}")
        return []

    product_search = response_GetProducts.json().get("data", {}).get("productSearch")
    if not product_search or not product_search.get("recordsFiltered"):
        print(f"{category}: products not found.")
        return []

    total_products = product_search["recordsFiltered"]
    print(f"{category}: {total_products} products found")

    allProducts = []

    page_size = 99 if "carrefour" in url_market else 16
    scraped_at = datetime.now(timezone.utc).isoformat()

    is_dia = "diaonline" in url_market
    empty_pages = 0
    MAX_EMPTY_PAGES = 2

    i = 0
    while True:
        page_from = i
        page_to = i + page_size - 1
        #stats["last_page_from"] = page_from
        #stats["last_page_to"] = page_to

        payload = payload_base.copy()
        payload["variables"] = payload_base["variables"].copy()
        payload["variables"]["from"] = page_from
        payload["variables"]["to"] = page_to

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            print(f"Error {response.status_code} paging {category} [{page_from}–{page_to}]")
            break

        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"{category} - Error parsing JSON in range {page_from}–{page_to}")
            print("Raw Response:", response.text[:300])
            break

        product_search = (data.get("data", {}) or {}).get("productSearch") or {}
        products = product_search.get("products") or []

        if not products:
            empty_pages += 1
            #stats["empty_pages"] = empty_pages
            print(f"{category} - Empty/No products in range {page_from}–{page_to}")

            if is_dia and empty_pages >= MAX_EMPTY_PAGES:
                break

            if not is_dia:
                break

            i += page_size
            continue

        empty_pages = 0
        #stats["empty_pages"] = 0

        for prd in products:
            #stats["total_api_products"] += 1
            try:
                items = prd.get("items") or []
                '''if not items:
                    stats["no_items"] += 1
                    continue'''

                item0 = items[0]

                product_reference = prd.get("productReference")
                ean = item0.get("ean") or product_reference

                sellers = item0.get("sellers") or []
                '''if not sellers:
                    stats["no_sellers"] += 1
                    continue'''

                offer = best_offer_from_sellers(sellers)
                if offer is None:
                    #stats["no_price"] += 1
                    #print(f"NO OFFER: {prd.get('productId')} - {prd.get('productName')}")
                    continue

                effective_price, regular_price = pick_prices(offer)
                '''if price is None or price <= 0:
                    stats["no_price"] += 1
                    continue'''

                # basics
                product_name = prd.get("productName")
                images = item0.get("images") or []
                image = images[0].get("imageUrl") if images else None
                brand = prd.get("brand")
                link = url_market.rstrip("/") + (prd.get("link") or "")

                product_id = prd.get("productId")
                item_id = item0.get("itemId")

                spec_groups = prd.get("specificationsGroups") or []
                all_specs = next((g["specifications"] for g in prd["specificationGroups"] if g["name"] == "allSpecifications"),[])
                envase= next((s["values"][0] for s in all_specs if s["name"] == "Envase Tipo"),None)
                
                # category
                categories = prd.get("categories") or []
                category_path = categories[0] if categories else None

                measurement_unit = item0.get("measurementUnit")
                unit_multiplier = item0.get("unitMultiplier")
                units_per_pack = unit_multiplier or 1

                brand_id = prd.get("brandId")

                price_valid_until = offer.get("PriceValidUntil")

                content_amount, content_unit, units_per_pack = parse_content(product_name or "")
                content_amount, content_unit = normalize_amount_unit(content_amount, content_unit)

                # defaults
                effective_reference_price = None
                regular_reference_price = None

                def to_ref_qty(amount, unit):
                    if amount in (None, 0) or unit is None:
                        return None, None
                    u = unit.lower()
                    if u == "ml":
                        return amount / 1000.0, "1 LT"
                    if u == "g" or u== "grs":
                        return amount / 1000.0, "1 Kg"
                    if u == "unit":
                        return amount, "1 UD"
                    return None, None

                ref_qty, ref_unit = to_ref_qty(content_amount, content_unit)

                effective_reference_price = safe_div(effective_price, ref_qty)
                regular_reference_price   = safe_div(regular_price, ref_qty)

                if effective_reference_price is not None:
                    effective_reference_price = round(effective_reference_price, 2)

                if regular_reference_price is not None:
                    regular_reference_price = round(regular_reference_price, 2)



                if is_dia:
                    product_reference = ean

                    measurement_unit = next((s["values"][0] for s in all_specs if s["name"] == "UnidaddeMedida"), None)
                    rr_price = next((s["values"][0] for s in all_specs if s["name"] == "PrecioPorUnd"), None)
                    pum = to_float(rr_price)

                    if pum not in (None, 0):
                        regular_reference_price = pum

                        content_ref = safe_div(regular_price, pum) 
                        effective_reference_price = safe_div(effective_price, content_ref)

                        if effective_reference_price is not None:
                            effective_reference_price = round(effective_reference_price, 2)

                        if content_amount is None and content_ref is not None:
                            mu = (measurement_unit or "").lower()
                            if "kg" in mu:
                                content_amount, content_unit = content_ref * 1000, "g"
                            elif "lt" in mu or re.search(r"\b(l|litro|litros)\b", mu):
                                content_amount, content_unit = content_ref * 1000, "ml"
                            elif "ud" in mu or re.search(r"\b(un|unidad|unidades)\b", mu):
                                content_amount, content_unit = content_ref, "unit"

                filtered = {
                    "source": market_name,
                    "scrapedAt": scraped_at,

                    "name": product_name,
                    "brand": brand,
                    "ean": ean,

                    "image": image,
                    "link": link,

                    "categoryPath": category_path,
                    "category": category,
                    
                    "regularPrice": regular_price,
                    "effectivePrice": effective_price,
                    "regularReferencePrice": regular_reference_price,
                    "effectiveReferencePrice": effective_reference_price,

                    "contentAmount": content_amount,
                    "contentUnit": content_unit,
                    
                    "unitsPerPack": units_per_pack,
                    "envase": envase,

                    "productId": product_id,
                    "itemId": item_id,
                    "productReference": product_reference,
                    "brand_id": brand_id,

                    "measurementUnit": measurement_unit,
                    "unitMultiplier": unit_multiplier,
                    "priceValidUntil": price_valid_until,
                    # "page_from": page_from,
                    # "page_to": page_to,
                }

                allProducts.append(filtered)
                #stats["saved"] += 1

            except Exception as e:
                print("ERROR:", repr(e), "productId:", prd.get("productId"), "name:", prd.get("productName"))
                raise

        if len(products) < page_size:
            break

        i += page_size

    #print(f"{category} debug stats: {stats}", flush=True)

    saved_count = len(allProducts)
    print(f"{category}: {saved_count} products saved.")
    return allProducts

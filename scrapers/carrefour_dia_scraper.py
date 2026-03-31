import json as _json
import math, random, time, re, asyncio
import aiohttp
import requests
from datetime import datetime, timezone
from scrapers.coto_scraper import get_attr
from utils.pricing import pick_prices
from utils.normalizador import (
    parse_content,
    normalize_amount_unit,
    safe_div,
    to_float,
)

# ---------------------------------------------------------------------------
# Helpers de precio de referencia
# ---------------------------------------------------------------------------

def _to_ref_qty(amount, unit):
    """Convierte amount/unit a la cantidad de referencia estándar (1L, 1Kg, 1Ud)."""
    if amount in (None, 0) or unit is None:
        return None, None
    u = unit.lower()
    if u == "ml":
        return amount / 1000.0, "1 LT"
    if u in ("g", "grs"):
        return amount / 1000.0, "1 Kg"
    if u == "unit":
        return amount, "1 UD"
    return None, None


# ---------------------------------------------------------------------------
# Selección de mejor oferta
# ---------------------------------------------------------------------------

def best_offer_from_sellers(sellers):
    """Retorna la commertialOffer con menor effectivePrice entre sellers disponibles."""
    best_off = None
    best_effective = None

    for s in sellers or []:
        if not s:
            continue

        off = s.get("commertialOffer") or {}
        effective_price, _ = pick_prices(off)
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


# ---------------------------------------------------------------------------
# Categorías
# ---------------------------------------------------------------------------

def _parse_dia_categories(menus):
    """Extrae slugs de categorías del formato de menú de Día."""
    slugs = set()
    for menu in menus:
        slug_root = menu.get("slug")
        if not slug_root:
            continue
        if "http" in slug_root:
            slug = slug_root.rstrip("/").split("/")[-1].split("?")[0]
        else:
            slug = slug_root.strip("/").split("?")[0]
        slugs.add(slug)
    return slugs


def _parse_carrefour_categories(menus):
    """Extrae slugs de categorías del formato de menú de Carrefour."""
    slugs = set()
    for menu in menus:
        if "menu" in menu and isinstance(menu["menu"], list):
            for subMenu in menu["menu"]:
                slug_root = subMenu.get("slug")
                if slug_root:
                    slug = slug_root.split("?")[0].strip("/").split("/")[0]
                    slugs.add(slug)

                for subsub in subMenu.get("menu") or []:
                    sub_slug = subsub.get("slug")
                    if sub_slug:
                        slug = sub_slug.split("?")[0].strip("/").split("/")[0]
                        slugs.add(slug)
        else:
            slug_root = menu.get("slug")
            if slug_root:
                slug = slug_root.rstrip("/").split("?")[0].split("/")[-1]
                slugs.add(slug)
    return slugs


# Mapa de parsers por market_name — extensible sin tocar la lógica central
_CATEGORY_PARSERS = {
    "carrefour": _parse_carrefour_categories,
    "dia": _parse_dia_categories,
}


def getCategoriesSlug(url_market, hash_value, sender, provider, market_name):
    """
    Consulta el endpoint de menú VTEX y retorna el set de slugs de categorías.

    market_name: 'carrefour' | 'dia'  — se pasa explícitamente para evitar
    detección frágil por URL.
    """
    url = f"{url_market.rstrip('/')}/_v/segment/graphql/v1"

    headers = {
        "Content-Type": "application/json",
        "Origin": url_market,
        "User-Agent": "Mozilla/5.0",
    }

    payload = {
        "operationName": "getMenus",
        "variables": {},
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": hash_value,
                "sender": sender,
                "provider": provider,
            },
            "variables": "eyJpc01vYmlsZSI6ZmFsc2V9",
        },
    }

    response = requests.post(url=url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"[{market_name}] Error {response.status_code} fetching categories")
        return set()

    body = response.json()
    errors = body.get("errors")
    if errors:
        print(
            f"[{market_name}] WARNING: categories query returned GraphQL errors "
            f"(hash={hash_value!r}). The persisted query hash may be stale. "
            f"Errors: {errors}"
        )

    menus = body.get("data", {}).get("menus", [])

    parser = _CATEGORY_PARSERS.get(market_name)
    if parser is None:
        print(f"[{market_name}] No category parser registered")
        return set()

    all_slugs = parser(menus)
    result = {slug for slug in all_slugs if slug and not slug.isdigit()}

    if not result:
        print(
            f"[{market_name}] WARNING: 0 categories returned. "
            f"The persisted query hash may be stale (hash={hash_value!r}). "
            f"Check that the hash is still valid at {url}."
        )

    return result


# ---------------------------------------------------------------------------
# Scraping de productos (async)
# ---------------------------------------------------------------------------

# Configuración por market — evita if/else dispersos por el código
_MARKET_CONFIG = {
    "carrefour": {"page_size": 99},
    "dia": {"page_size": 16},
}


async def scrapeProducts(
    session, url_market, category, hash_value, sender, provider, map_value, market_name
):
    """
    Scraping paginado de productos para una categoría VTEX.

    market_name: 'carrefour' | 'dia'  — se pasa explícitamente.
    """
    config = _MARKET_CONFIG.get(market_name, {"page_size": 50})
    page_size = config["page_size"]
    is_dia = market_name == "dia"

    url = f"{url_market.rstrip('/')}/_v/segment/graphql/v1"
    headers = {
        "Content-Type": "application/json",
        "Origin": url_market,
        "User-Agent": "Mozilla/5.0",
    }

    is_category_id = category.isdigit()

    payload_base = {
        "operationName": "productSearchV3",
        "variables": {
            "hideUnavailableItems": True,
            "skusFilter": "ALL_AVAILABLE",
            "query": "" if is_category_id else category,
            "from": 0,
            "to": 1,
            "selectedFacets": [{"key": "c", "value": category}],
            "map": "c" if is_category_id else map_value,
            "orderBy": "OrderByNameASC",
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": hash_value,
                "sender": sender,
                "provider": provider,
            }
        },
    }

    # --- Primer request: obtener total de productos ---
    # Forzamos UTF-8 explícito para evitar mojibake cuando el servidor
    # no declara charset en el Content-Type header.
    try:
        async with session.post(url, headers=headers, json=payload_base) as resp:
            if resp.status != 200:
                print(f"[{market_name}] {category} - Error {resp.status} on first poll")
                return []
            raw = await resp.read()
            data = _json.loads(raw.decode("utf-8"))
    except Exception as e:
        print(f"[{market_name}] {category} - Exception on first poll: {e}")
        return []

    product_search = data.get("data", {}).get("productSearch")
    if not product_search or not product_search.get("recordsFiltered"):
        return []

    total_products = product_search["recordsFiltered"]
    print(f"[{market_name}] {category}: {total_products} products found")

    all_products = []
    scraped_at = datetime.now(timezone.utc).isoformat()
    empty_pages = 0
    MAX_EMPTY_PAGES = 2
    i = 0

    while True:
        page_from = i
        page_to = i + page_size - 1

        payload = {**payload_base, "variables": {**payload_base["variables"], "from": page_from, "to": page_to}}

        try:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    print(f"[{market_name}] Error {resp.status} paging {category} [{page_from}–{page_to}]")
                    break
                try:
                    raw = await resp.read()
                    data = _json.loads(raw.decode("utf-8"))
                    if not isinstance(data, dict):
                        print(f"[{market_name}] {category} - Unexpected response (not a dict) [{page_from}–{page_to}]")
                        break
                except Exception:
                    text = await resp.text(encoding="utf-8", errors="replace")
                    print(f"[{market_name}] {category} - JSON parse error [{page_from}–{page_to}]: {text[:200]}")
                    break
        except Exception as e:
            print(f"[{market_name}] Exception paging {category} at {page_from}: {e}")
            break

        products = (data.get("data", {}) or {}).get("productSearch", {}).get("products") or []

        if not products:
            empty_pages += 1
            if is_dia and empty_pages >= MAX_EMPTY_PAGES:
                break
            if not is_dia:
                break
            i += page_size
            continue

        empty_pages = 0

        for prd in products:
            try:
                items = prd.get("items") or []
                if not items:
                    continue
                item0 = items[0]

                product_reference = prd.get("productReference")
                ean = item0.get("ean") or product_reference

                sellers = item0.get("sellers") or []
                offer = best_offer_from_sellers(sellers)
                if offer is None:
                    continue

                effective_price, regular_price = pick_prices(offer)

                product_name = prd.get("productName")
                images = item0.get("images") or []
                image = images[0].get("imageUrl") if images else None
                brand = prd.get("brand")
                link = url_market.rstrip("/") + (prd.get("link") or "")

                product_id = prd.get("productId")
                item_id = item0.get("itemId")
                brand_id = prd.get("brandId")
                price_valid_until = offer.get("PriceValidUntil")

                # Especificaciones
                all_specs = next(
                    (
                        g["specifications"]
                        for g in prd.get("specificationGroups") or []
                        if g.get("name") == "allSpecifications"
                    ),
                    [],
                )
                envase = next(
                    (s["values"][0] for s in all_specs if s["name"] == "Envase Tipo"),
                    None,
                )

                # Categoría
                categories = prd.get("categories") or []
                category_path = categories[0] if categories else None

                measurement_unit = item0.get("measurementUnit")
                unit_multiplier = item0.get("unitMultiplier")

                # Contenido desde nombre del producto
                content_amount, content_unit, units_per_pack = parse_content(product_name or "")
                content_amount, content_unit = normalize_amount_unit(content_amount, content_unit)

                # Precio de referencia por unidad estándar
                ref_qty, _ = _to_ref_qty(content_amount, content_unit)
                effective_reference_price = safe_div(effective_price, ref_qty)
                regular_reference_price = safe_div(regular_price, ref_qty)

                if effective_reference_price is not None:
                    effective_reference_price = round(effective_reference_price, 2)
                if regular_reference_price is not None:
                    regular_reference_price = round(regular_reference_price, 2)

                # Lógica adicional específica de Día
                if is_dia:
                    product_reference = ean
                    measurement_unit = next(
                        (s["values"][0] for s in all_specs if s["name"] == "UnidaddeMedida"),
                        None,
                    )
                    rr_price = next(
                        (s["values"][0] for s in all_specs if s["name"] == "PrecioPorUnd"),
                        None,
                    )
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

                all_products.append({
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
                })

            except Exception as e:
                print(f"[{market_name}] Error parsing product in {category}: {type(e).__name__}: {e}")

        if len(products) < page_size:
            break

        i += page_size

    return all_products


# ---------------------------------------------------------------------------
# Orquestación async de todas las categorías
# ---------------------------------------------------------------------------

async def _bounded_scrape(
    semaphore, session, url_market, category, hash_value, sender, provider, map_value, market_name
):
    async with semaphore:
        return await scrapeProducts(
            session, url_market, category, hash_value, sender, provider, map_value, market_name
        )


async def run_all_categories_async(
    url_market, categories, hash_value, sender, provider, map_value, market_name, max_concurrent=20
):
    semaphore = asyncio.Semaphore(max_concurrent)
    connector = aiohttp.TCPConnector(limit=max_concurrent)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            _bounded_scrape(
                semaphore, session, url_market, cat,
                hash_value, sender, provider, map_value, market_name
            )
            for cat in sorted(categories)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_products = []
    for r in results:
        if isinstance(r, Exception):
            print(f"[{market_name}] Task raised unhandled exception: {type(r).__name__}: {r}")
        elif r:
            all_products.extend(r)

    if not all_products:
        print(
            f"[{market_name}] WARNING: 0 products scraped across all {len(categories)} categories. "
            f"The persisted query hash may be stale (hash={hash_value!r}). "
            f"Verify the hash is still valid for productSearchV3."
        )

    return all_products

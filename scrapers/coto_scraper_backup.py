from ast import parse
from sys import base_prefix
from bs4 import BeautifulSoup
import os, json, requests, time, math, re, random
from datetime import datetime

start_time = time.time()
market_name = "coto"



#
# Utils parseo basicos 
#
def parse_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default
    
def parse_float(value, default=None):
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.strip().replace(",", ".")
        return float(value)
    except (TypeError, ValueError):
        return default
    
def get_attr(attributes, key):
    value = attributes.get(key, [None])
    return value[0] if value else None



#
# Categorias
#
def get_categories_slugs_coto(url_market):
    url = f"{url_market}/rest/model/atg/actors/cBackOfficeActor/getCategorias"

    headers = {
        "Origin": url_market,
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    }
    payload = {"state": "closed"}

    try:
        response_categories = requests.post(url=url, headers=headers, json=payload)
        response_categories.raise_for_status()
    except requests.RequestException as e:
        print(f"Error making the request: {e}")
        return []

    try:
        data = response_categories.json()
        output_list = data.get("output", [])
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return []

    categories_dict = []

    for entry in output_list:
        try:
            top_level = entry.get("topLevelCategory")
            if top_level:
                display_name = top_level.get("displayName")
                slug = top_level.get("navigationState")
                if display_name and slug:
                    categories_dict.append({
                        "name": display_name.strip(),
                        "slug": slug.strip()
                    })
        except Exception as e:
            print(f"Error processing category: {e}")

    return categories_dict



#
# Pesables por kilo
#
def is_weighable_kg(attributes, name=""):
    es_pesable = get_attr(attributes, "product.unidades.esPesable")
    if str(es_pesable).strip() == "1":
        return True

    desc_unidad = (get_attr(attributes, "product.unidades.descUnidad") or "").strip().upper()
    if desc_unidad in ("KGS", "KG", "KILO"):
        return True

    if name and re.search(r"\bx\s*kg\b|\bx\s*kilo\b", name.lower()):
        return True

    return False



#
#
#
def safe_get_json(url, headers, max_tries=10, timeout=20, base_sleep=0.6):
    last_err = None

    for i in range(max_tries):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)

            # Si rate limit / server issues, reintentar
            if r.status_code in (429, 500, 502, 503, 504):
                raise ValueError(f"HTTP {r.status_code}")

            r.raise_for_status()

            ct = (r.headers.get("Content-Type") or "").lower()
            text = (r.text or "").strip()

            # Si parece HTML o está vacío, no intentes json()
            if not text or text.startswith("<") or ("text/html" in ct):
                snippet = text[:120].replace("\n", " ")
                raise ValueError(f"Non-JSON body (ct={ct}) snippet='{snippet}'")

            return r.json()

        except Exception as e:
            last_err = e
            # backoff + jitter
            sleep_s = base_sleep * (2 ** i) + random.uniform(0, 0.25)
            time.sleep(sleep_s)

    raise last_err

#
# Parse content + packs
#
def parse_measurement_and_multiplier(text):
    """
    Extrae "cantidad + unidad" del texto.
    Devuelve (unit, amount)
    """
    if not text:
        return ("unit", 1.0)

    s = str(text).strip().lower()
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(cc|ml|l|lt|lts|g|gr|grs|grm|kg)\b", s)
    if not m:
        return ("unit", 1.0)

    amount = float(m.group(1).replace(",", "."))
    unit = m.group(2)

    unit_map = {
        "g": "g", "gr": "g", "grs": "g", "grm": "g",
        "kg": "kg",
        "ml": "ml",
        "cc": "cc",
        "l": "lt", "lt": "lt", "lts": "lt",
        "litro": "lt", "litros": "lt"
    }
    return (unit_map.get(unit, unit), amount)

def parse_units_per_pack(text: str):
    if not text:
        return None

    s = text.lower()

    m = re.search(r"(\d+)\s*(?:unidades|unidad|un|u|ud)\b", s)
    if m:
        return int(m.group(1))

    m = re.search(r"x\s*(\d+)\b", s)
    if m:
        return int(m.group(1))

    return None

def parse_contenido_pack(text):
    if not text or not isinstance(text, str):
        return None, None, None, None

    unit, unit_amount = parse_measurement_and_multiplier(text)
    if unit == "unit":
        return None, None, None, None

    units_per_pack = parse_units_per_pack(text)
    if units_per_pack and units_per_pack > 1:
        total = unit_amount * units_per_pack
    else:
        total = unit_amount
        units_per_pack = 1

    return unit_amount, unit, units_per_pack, total



#
# Paths categories
#
def build_category_path_coto(all_ancestors):
    if not all_ancestors or not isinstance(all_ancestors, list):
        return None

    blacklist = {"CotoDigital", "Home", "Inicio", "Productos"}
    cleaned = [c.strip() for c in all_ancestors if c and c.strip() and c not in blacklist]
    if not cleaned:
        return None

    # dedupe
    seen = set()
    ordered = []
    for c in cleaned:
        if c not in seen:
            seen.add(c)
            ordered.append(c)

    priority = {"Almacén": 0, "Bebidas": 0, "Limpieza": 0, "Perfumería": 0, "Congelados": 0, "Frescos": 0}
    ordered.sort(key=lambda x: priority.get(x, 10))

    return "/" + "/".join(ordered) + "/"



#
# Prices 
#
def extract_price_from_text(text):
    """
    Extrae un precio numérico desde strings tipo:
    'Precio Contado: $2848'
    '$1.851,20 c/u'
    'Precio: $ 2.999,99'
    """
    if not text or not isinstance(text, str):
        return None

    s = text.lower()

    # buscar número con $ opcional
    m = re.search(r"\$?\s*([\d\.,]+)", s)
    if not m:
        return None

    number_str = m.group(1)

    # normalizar separadores
    if "," in number_str and "." in number_str:
        # 1.234,56
        number_str = number_str.replace(".", "").replace(",", ".")
    else:
        number_str = number_str.replace(",", ".")

    try:
        return float(number_str)
    except ValueError:
        return None

def extract_discount_price(attributes, key="precioDescuento"):
    raw_list = attributes.get("product.dtoDescuentos", [])
    if not raw_list:
        return None

    raw_discount = raw_list[0]
    if not raw_discount:
        return None

    try:
        discounts = json.loads(raw_discount)
        if not (isinstance(discounts, list) and discounts):
            return None

        price_str = discounts[0].get(key)
        if not price_str or not isinstance(price_str, str):
            return None

        s = price_str.strip().lower()

        # 1) Filtrar textos que suelen NO ser precio (porcentajes / cantidades)
        #    Ej: "50% 2da" / "Llevando 2" / "2da unidad"
        if "%" in s:
            return None
        if "llevando" in s or "2da" in s or "unidad" in s:
            # si no hay $ (precio explícito), no es confiable
            if "$" not in s:
                return None

        # 2) Preferir números precedidos por $ si existe
        m = re.search(r"\$\s*([\d\.,]+)", s)
        if m:
            number_str = m.group(1)
        else:
            # 3) Si no hay $, aceptar solo si parece precio unitario (c/u)
            if "c/u" not in s and "cu" not in s:
                return None
            m2 = re.search(r"([\d\.,]+)", s)
            if not m2:
                return None
            number_str = m2.group(1)

        # 4) Normalizar separadores (1.234,56 / 1,234.56 / 733,85)
        if number_str.count(",") == 1 and number_str.count(".") == 0:
            return float(number_str.replace(",", "."))
        if number_str.count(".") == 1 and number_str.count(",") == 0:
            return float(number_str)
        if number_str.count(",") == 1 and number_str.count(".") == 1:
            # asumir 1.234,56
            return float(number_str.replace(".", "").replace(",", "."))
        return float(number_str.replace(",", "."))

    except Exception:
        return None



#
# Reference price por kg/l
#
def base_factor_from_total(content_unit, content_amount):
    if content_amount is None:
        return None

    if content_unit == "gr" or content_unit == "g":
        return content_amount / 1000.0
    if content_unit == "kg":
        return content_amount
    if content_unit in ("ml", "cc"):
        return content_amount / 1000.0
    if content_unit == "l":
        return content_amount
    return None



#
# Scraper
# 
def get_products_coto(url_market, categories):
    products_per_page=24
    main_url = "https://www.cotodigital.com.ar"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    current_millis = int(time.time() * 1000)

    allProducts = []

    for cat in categories:
        display_name = cat["name"]
        slug = cat["slug"]
        url_base = (
            f"{url_market}/sitios/cdigi/{slug}"
            f"?Nf=product.endDate|GTEQ+{current_millis}|product.startDate|LTEQ+{current_millis}"
            f"&No=0&Nrpp=24&format=json"
        )

        try:
            response_init = requests.get(url=url_base, headers=headers)
            response_init.raise_for_status()
            data_init = response_init.json()
        except Exception as e:
            print(f"Initial error in {display_name}: {e}")
            continue

        total_products = 0
        for block in data_init.get("contents", []):
            if isinstance(block, dict) and "Main" in block:
                try:
                    total_products = block["Main"][2]["contents"][0]["totalNumRecs"]
                    break
                except Exception:
                    continue

        if total_products == 0:
            print(f"{display_name}: products not found.")
            continue
        
        print(f"Found in {display_name}: {total_products} products")
        pages_range = math.ceil(total_products / products_per_page)

        for page in range(pages_range):
            url_by_page = (
                f"{url_market}/sitios/cdigi/{slug}"
                f"?Nf=product.endDate|GTEQ+{current_millis}|product.startDate|LTEQ+{current_millis}"
                f"&No={page * products_per_page}&Nrpp={products_per_page}&format=json"
            )

            try:
                response_by_page = requests.get(url=url_by_page, headers=headers)
                response_by_page.raise_for_status()
                try:
                    data_by_page = safe_get_json(url_by_page, headers)
                except Exception as e:
                    print(f"Error page {display_name} {page}: {e}")
                    continue
            except Exception as e:
                print(f"Error page {display_name} {page}: {e}")
                continue

            contents = data_by_page.get("contents", [])
            if not contents or "Main" not in contents[0] or len(contents[0]["Main"]) < 3:
                print(f"Empty page {display_name} - Page {page}")
                continue
                
            products_data = contents[0]["Main"][2]["contents"][0].get("records", [])
            if not products_data:
                print(f"No products {display_name} - Page {page}")
                continue

            scraped_at = datetime.now().isoformat()

            for data in products_data:
                nested_records = data.get("records", [])
                if not nested_records:
                    continue

                for nested in nested_records:
                    try:
                        attributes = nested.get("attributes", {}) or {}

                        # link
                        record_state = (
                            nested.get("detailsAction", {}).get("recordState")
                            or data.get("detailsAction", {}).get("recordState")
                            or ""
                        )
                        link = (main_url + "/sitios/cdigi/productos" + record_state.split("?")[0]) if record_state else None

                        # basics
                        name = (get_attr(attributes, "product.displayName") or get_attr(attributes, "sku.displayName") or "").strip()
                        image = (get_attr(attributes, "product.largeImage.url") or get_attr(attributes, "product.mediumImage.url") or None)
                        brand = get_attr(attributes, "product.brand") or get_attr(attributes, "product.MARCA")
                        ean = get_attr(attributes, "product.eanPrincipal")

                        product_id = get_attr(attributes, "product.repositoryId")      # prod00229480
                        item_id = get_attr(attributes, "sku.repositoryId")            # sku00229480
                        product_reference = get_attr(attributes, "record.id")         # 00229480-...-200

                        envase = get_attr(attributes, "product.ENVASE")

                        # category
                        category = get_attr(attributes, "product.category") or get_attr(attributes, "product.FAMILIA") or display_name
                        raw_ancestors = attributes.get("allAncestors.displayName")
                        category_path = build_category_path_coto(raw_ancestors)

                        # base content
                        contenido_raw = get_attr(attributes, "product.CONTENIDO") or get_attr(attributes, "product.VOLUMEN") or ""
                        content_unit, unit_multiplier = parse_measurement_and_multiplier(contenido_raw)

                        if content_unit == "unit":
                            u2, m2 = parse_measurement_and_multiplier(name)
                            if u2 != "unit":
                                content_unit, unit_multiplier = u2, m2

                        units_per_pack = 1
                        content_amount = unit_multiplier

                        # packs
                        if envase and "PACK" in str(envase).upper():
                            unit_amt, unit_u, upp, total_amt = parse_contenido_pack(contenido_raw)
                            if unit_amt is not None:
                                content_unit = unit_u
                                units_per_pack = upp
                                content_amount = total_amt
                                if content_amount < 50:
                                    content_amount = content_amount * 100

                        # precios
                        discounts_raw = attributes.get("product.dtoDescuentos", [])
                        discounts = []
                        if isinstance(discounts_raw, list) and discounts_raw and isinstance(discounts_raw[0], str):
                            try:
                                discounts = json.loads(discounts_raw[0])
                            except Exception:
                                discounts = []

                        regular_price = None
                        if discounts:
                            regular_price = extract_price_from_text(discounts[0].get("textoPrecioRegular"))
                        if regular_price is None:
                            regular_price = parse_float(get_attr(attributes, "sku.activePrice"))

                        effective_price = None
                        if discounts:
                            d = discounts[0]
                            texto_desc = (d.get("textoDescuento") or "").lower()
                            texto_llev = (d.get("textoLlevando") or "").lower()

                            is_bundle = ("2x1" in texto_desc) or ("3x2" in texto_desc) or ("llevando" in texto_llev) or ("2da" in texto_desc) or re.search(r"\bx\s*\d+\b", texto_desc)
                            if not is_bundle:
                                effective_price = extract_price_from_text(d.get("precioDescuento"))

                        if effective_price is None:
                            effective_price = regular_price

                        # reference regular: Coto lo trae, pero puede ser inconsistente en packs
                        regular_reference_price = parse_float(get_attr(attributes, "sku.referencePrice"))

                        # pesables x kg: referencia = precio
                        weighable = is_weighable_kg(attributes, name)
                        if weighable:
                            content_unit = "kg"
                            content_amount = 1.0
                            units_per_pack = 1
                            regular_reference_price = regular_price
                            effective_reference_price = effective_price
                        else:
                            bf = base_factor_from_total(content_unit, content_amount)
                            if bf and bf > 0 and effective_price is not None:
                                effective_reference_price = effective_price / bf
                                if content_amount < 50:
                                    effective_reference_price= effective_reference_price/10
                                
                            else:
                                effective_reference_price = regular_reference_price

                        # redondeo
                        if effective_reference_price is not None:
                            effective_reference_price = round(effective_reference_price, 2)

                        filtered = {
                            "source": market_name,
                            "scrapedAt": scraped_at,

                            "name": name,
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
                        
                            #"offerType": offers_type,
                            #"offerText": offer_text,

                            "productId": product_id,
                            "itemId": item_id,
                            "productReference": product_reference,
                            
                            #"brand_id": brand_id,
                            #"unitMultiplier": unit_multiplier,
                            #"priceValidUntil": None,
                        }

                        if effective_price is None:
                            print("[DEBUG] effective_price None:", name)

                        allProducts.append(filtered)

                    except Exception as e:
                        print("[ERROR]", e, "product:", name)
                        continue
        #time.sleep(0.25 + random.uniform(0, 0.15))

    print(f"TOTAL: {len(allProducts)} products saved.")
    return allProducts

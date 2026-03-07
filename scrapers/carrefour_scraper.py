from bs4 import BeautifulSoup
import requests
import json
import os
import time
import datetime

startTime = time.time()

# Function to retrieve all product category slugs from Carrefour's menu
def getCategorySlug():
    url = "https://www.carrefour.com.ar/_v/segment/graphql/v1"

    headers = {
        "Content-Type": "application/json",
        "Origin": "https://www.carrefour.com.ar",
        "User-Agent": "Mozilla/5.0"
    }

    payload_categories = {
        "operationName": "getMenus",
        "variables": {},
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "107835072b509adb39002442c46fab9ecf2699dc0dae4fa94a0336298da00b94",
                "sender": "carrefourar.mega-menu@0.x",
                "provider": "carrefourar.mega-menu@0.x"
            },
            "variables": "eyJpc01vYmlsZSI6ZmFsc2V9"
        }
    }

    # Send POST request to fetch menu structure
    responseCategories = requests.post(url, headers=headers, json=payload_categories)

    if responseCategories.status_code != 200:
        print(f"Error {responseCategories.status_code}: {responseCategories.text}")
        return set()

    data = responseCategories.json()
    menus = data.get("data", {}).get("menus", [])

    category_slugs = set()

    # Traverse the menu structure and extract category slugs
    for menu in menus:
        if "menu" in menu:
            for sub in menu["menu"]:
                slug_root = sub.get("slug")
                if slug_root:
                    slug = slug_root.split("?")[0].strip("/").split("/")[0]
                    category_slugs.add(slug)

                if "menu" in sub and isinstance(sub["menu"], list):
                    for subsub in sub["menu"]:
                        sub_slug_root = subsub.get("slug")
                        if sub_slug_root:
                            slug = sub_slug_root.split("?")[0].strip("/").split("/")[0]
                            category_slugs.add(slug)

    # Traverse the menu structure and extract category slugs
    return category_slugs



# Function to scrape products by category slug
def scrapeProducts(slug):
    url = "https://www.carrefour.com.ar/_v/segment/graphql/v1"

    headers = {
        "Content-Type": "application/json",
        "Origin": "https://www.carrefour.com.ar",
        "User-Agent": "Mozilla/5.0"
    }

    # Prepare base payload to search products by slug
    payload_base = {
        "operationName": "productSearchV3",
        "variables": {
            "hideUnavailableItems": True,
            "skusFilter": "ALL_AVAILABLE",
            "query": "",
            "from": 0,
            "to": 0,
            "selectedFacets": [
                { "key": "c", "value": slug }
            ],
            "map": "c",
            "orderBy": "OrderByNameASC"
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "c351315ecde7f473587b710ac8b97f147ac0ac0cd3060c27c695843a72fd3903"
            }
        }
    }

    # Initial request to get total number of products
    response_GetProducts = requests.post(url, headers=headers, json=payload_base)

    if response_GetProducts.status_code != 200:
        print(f"{slug} - Error {response_GetProducts.status_code}")
        return

    product_search = response_GetProducts.json().get("data", {}).get("productSearch")
    if not product_search or not product_search.get("recordsFiltered"):
        print(f"{slug}: products not found.")
        return

    total = product_search["recordsFiltered"]
    print(f"🔍 {slug}: {total} products found")

    allProducts = []
    page_size = 99 # Max products per page

    # Paginate through all products
    for i in range(0, total, page_size):
        payload = payload_base.copy()
        payload["variables"] = payload_base["variables"].copy()
        payload["variables"]["from"] = i
        payload["variables"]["to"] = min(i + page_size - 1, total - 1)

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            print(f"Error {response.status_code} paging {slug}")
            continue

        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"{slug} - Error parsing JSON in range {i}–{i + page_size - 1}")
            print("Raw Response:", response.text[:300])  # muestra parte de la respuesta
            continue

        product_search = data.get("data", {}).get("productSearch")

        if not product_search or "products" not in product_search:
            print(f"{slug} - No products in range {i}–{i + page_size - 1}")
            continue

        products = product_search["products"]

        # Extract relevant product fields
        for prd in products:
            try:
                product = prd.get("productName")
                link = "https://www.carrefour.com.ar" + prd.get("link", "")
                image = prd["items"][0]["images"][0]["imageUrl"]

                seller_info = prd["items"][0]["sellers"][0]["commertialOffer"]
                spotPrice = seller_info.get("spotPrice")
                price = seller_info.get("Price")
                listPrice = seller_info.get("ListPrice")

                if all(p is not None and p > 0 for p in (spotPrice, price, listPrice)):
                    filtered = {
                        "name": product,
                        "spotPrice": spotPrice,
                        "price": price,
                        "listPrice": listPrice,
                        "image": image,
                        "link": link,
                        "category": slug,
                    }
                    allProducts.append(filtered)
            except Exception as e:
                continue

    # Save results if any products were found
    if allProducts:
        current_date = datetime.datetime.now()
        formated_date = current_date.strftime("%Y_%m_%d")
        os.makedirs("data/results", exist_ok=True)
        filepath = f"data/results/test_carrefour_prices_{formated_date}.json"

        existing = []
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        existing = json.loads(content)
            except Exception as e:
                print(f"Error reading JSON existing: {e}")
        else:
            existing = []

        # Append new products to existing ones
        existing.extend(allProducts)

        # Save combined data to file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

        print(f"{slug}: {len(allProducts)} products saved.")
    else:
        print(f"{slug}: without filterable products.")
    



# Main scraper function, receives a set of category slugs or fetches a default list for testing
def runCarrefourScraper(slugs=None):
    if slugs is None:
            print("Obtaining available categories from Carrefour...")
            slugs = getCategorySlug()
            print(f"{len(slugs)} categories found.")
    if not slugs:
        print("No categories found for scraping.")
        return
    
    """
    #Test categorias acotado
    if slugs is None:
        slugs = {"Bebidas", "Carnes-y-Pescados", "lacteos-y-productos-frescos", "panaderia"}
    """
    
    # Iterate through each category and scrape products
    for slug in slugs:
        scrapeProducts(slug)
    
    end_time = time.time()
    elapsed_time = end_time - startTime
    print(f"\nTotal execution time: {elapsed_time:.2f} seconds")
import json
import os
import time
import asyncio
from datetime import datetime

from data.db import persist_market_snapshot, refresh_latest_prices
from scrapers.coto_scraper import (
    get_categories_slugs_coto, 
    get_products_coto
)
from scrapers.carrefour_dia_scraper import (
    getCategoriesSlug,
    run_all_categories_async
)

DIA_CATEGORIES_PARAMS = {
    "hash_value": "c883ea1b5de32e20496897a8339fc6dd7ecc7e2ad571baadba9be2113d395a32",
    "sender": "diaio.custom-mega-menu@0.x", 
    "provider": "diaio.extended-mega-menu@0.x"
}

CARREFOUR_CATEGORIES_PARAMS = {
    "hash_value": "5415e7bbf2b8b17612811bd41448e2de5e5ac97a68b586a6b84bed5697e2e2e5",
    "sender": "carrefourar.mega-menu@0.x", 
    "provider": "carrefourar.mega-menu@0.x"
}

COMMON_SEARCH_PARAMS = {
    "hash_value": "31d3fa494df1fc41efef6d16dd96a96e6911b8aed7a037868699a1f3f4d365de",
    "sender": "vtex.store-resources@0.x",
    "provider": "vtex.search-graphql@0.x"
}

DEBUG_ONE_CATEGORY = False


def persist_market_online(market_name: str, market_url: str, products: list):
    result = persist_market_snapshot(
        market_code=market_name,
        market_url=market_url,
        products=products,
    )

    if result.get("enabled"):
        print(
            f"DB {market_name.upper()}: {result['snapshots_inserted']} snapshots inserted "
            f"({result['errors']} errors)."
        )
        return

    reason = result.get("reason", "disabled")
    if reason == "missing_database_url":
        print("DB disabled: set COMPARAR_DATABASE_URL (or DATABASE_URL) to enable online persistence.")
    elif reason == "missing_psycopg_dependency":
        print("DB disabled: install dependency `psycopg[binary]`.")
    else:
        print(f"DB {market_name.upper()} error: {result.get('error', reason)}")

def save_market_snapshot(market_name: str, products: list):
    formated_date = datetime.now().strftime("%Y_%m_%d")
    output_dir = f"data/results/{market_name}"
    os.makedirs(output_dir, exist_ok=True)
    filepath = f"{output_dir}/{market_name}_prices_{formated_date}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    return filepath

def run_carrefour():
    url_market = "https://www.carrefour.com.ar"
    market_name = "carrefour"

    print("Scraping CARREFOUR...")
    carrefour_categories = getCategoriesSlug(
        url_market,
        **CARREFOUR_CATEGORIES_PARAMS
    )

    DEBUG_CATEGORY = "bebidas"

    if DEBUG_ONE_CATEGORY:
        carrefour_categories = [
            c for c in carrefour_categories
            if DEBUG_CATEGORY.lower() in str(c).lower()
        ]
        if not carrefour_categories:
            print(f"[DEBUG] No categories matched '{DEBUG_CATEGORY}'.")
            return
        print(f"[DEBUG] Scraping only categories: {carrefour_categories}")

    print(f"Categories to scrape: {len(carrefour_categories)}")
    
    all_products_unified = asyncio.run(run_all_categories_async(
        url_market,
        carrefour_categories,
        hash_value=COMMON_SEARCH_PARAMS["hash_value"],
        sender=COMMON_SEARCH_PARAMS["sender"],
        provider=COMMON_SEARCH_PARAMS["provider"],
        map_value="c"
    ))
    
    total_saved = len(all_products_unified)

    if all_products_unified:
        filepath = save_market_snapshot(market_name, all_products_unified)
        print(f"TOTAL {market_name.upper()}: {total_saved} products saved.")
        print(f"Saved snapshot: {filepath}")
        persist_market_online(market_name, url_market, all_products_unified)
        refresh_latest_prices(market_name)
    else:
        print(f"TOTAL {market_name.upper()}: 0 products saved.")

    print("CARREFOUR done.\n")


def run_dia():
    url_market = "https://diaonline.supermercadosdia.com.ar"
    market_name = "dia"

    print("Scraping DIA...")

    dia_categories = getCategoriesSlug(
        url_market,
        **DIA_CATEGORIES_PARAMS
    )

    DEBUG_CATEGORY = "bebidas"

    if DEBUG_ONE_CATEGORY:
        dia_categories = [
            c for c in dia_categories
            if DEBUG_CATEGORY.lower() in str(c).lower()
        ]
        if not dia_categories:
            print(f"[DEBUG] No categories matched '{DEBUG_CATEGORY}'.")
            return
        print(f"[DEBUG] Scraping only categories: {dia_categories}")

    print(f"Categories to scrape: {len(dia_categories)}")
    
    all_products_unified = asyncio.run(run_all_categories_async(
        url_market,
        dia_categories,
        hash_value=COMMON_SEARCH_PARAMS["hash_value"],
        sender=COMMON_SEARCH_PARAMS["sender"],
        provider=COMMON_SEARCH_PARAMS["provider"],
        map_value="c"
    ))
    
    total_saved = len(all_products_unified)

    if all_products_unified:
        filepath = save_market_snapshot(market_name, all_products_unified)
        print(f"TOTAL {market_name.upper()}: {total_saved} products saved.")
        print(f"Saved snapshot: {filepath}")
        persist_market_online(market_name, url_market, all_products_unified)
        refresh_latest_prices(market_name)
    else:
        print(f"TOTAL {market_name.upper()}: 0 products saved.")

    print("DIA done.\n")


def run_coto():
    url_market = "https://www.cotodigital.com.ar"
    market_name="coto"

    print("Scraping COTO...")

    categories = get_categories_slugs_coto(url_market)
    c=0
    if DEBUG_ONE_CATEGORY and len(categories) > c:
        cat = categories[c]
        categories = [cat]
        print(f"[DEBUG] Scraping only category: {cat}")

    allProducts = get_products_coto(url_market, categories) or []

    formated_date = datetime.now().strftime("%Y_%m_%d")
    output_dir = f"data/results/{market_name}"
    os.makedirs(output_dir, exist_ok=True)
    filepath = f"{output_dir}/{market_name}_prices_{formated_date}.json"

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(allProducts, f, ensure_ascii=False, indent=2)

        print(f"TOTAL {market_name.upper()}: {len(allProducts)} products saved.")
        persist_market_online(market_name, url_market, allProducts)
        refresh_latest_prices(market_name)
    except Exception as e:
        print(f"{market_name.upper()}: failed to save file - Error: {e}")

    print("COTO done.\n")


if __name__ == "__main__":
    start_time = time.time()
    run_carrefour()
    run_dia()
    run_coto()
    print(f"Total time: {round((time.time() - start_time)/60, 2)} minutes.")

import json
import os
import time
import asyncio
import argparse
from datetime import datetime

from data.db import persist_market_snapshot, refresh_latest_prices
from data.cba import update_cba_current_month
from scrapers.coto_scraper import (
    get_categories_slugs_coto,
    get_products_coto,
)
from scrapers.carrefour_dia_scraper import (
    getCategoriesSlug,
    run_all_categories_async,
)

# ---------------------------------------------------------------------------
# Configuración por mercado VTEX
# ---------------------------------------------------------------------------

VTEX_MARKETS = {
    "carrefour": {
        "url": "https://www.carrefour.com.ar",
        "categories_params": {
            "hash_value": "823787add87738768b74a9246699764aacab9c6e2ca5783173e2aac6ec4b3eda",
            "sender": "carrefourar.mega-menu@0.x",
            "provider": "carrefourar.mega-menu@0.x",
        },
    },
    "dia": {
        "url": "https://diaonline.supermercadosdia.com.ar",
        "categories_params": {
            "hash_value": "c883ea1b5de32e20496897a8339fc6dd7ecc7e2ad571baadba9be2113d395a32",
            "sender": "diaio.custom-mega-menu@0.x",
            "provider": "diaio.extended-mega-menu@0.x",
        },
    },
}

COMMON_SEARCH_PARAMS = {
    "hash_value": "31d3fa494df1fc41efef6d16dd96a96e6911b8aed7a037868699a1f3f4d365de",
    "sender": "vtex.store-resources@0.x",
    "provider": "vtex.search-graphql@0.x",
}

DEBUG_ONE_CATEGORY = False
DEBUG_CATEGORY_NAME = "bebidas"


# ---------------------------------------------------------------------------
# Helpers compartidos
# ---------------------------------------------------------------------------

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
    formatted_date = datetime.now().strftime("%Y_%m_%d")
    output_dir = f"data/results/{market_name}"
    os.makedirs(output_dir, exist_ok=True)
    filepath = f"{output_dir}/{market_name}_prices_{formatted_date}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    return filepath


# ---------------------------------------------------------------------------
# Scrapers
# ---------------------------------------------------------------------------

def run_vtex_market(market_name: str):
    """Ejecuta el scraping completo para un mercado VTEX (Carrefour o Día)."""
    config = VTEX_MARKETS[market_name]
    url_market = config["url"]
    cat_params = config["categories_params"]

    print(f"Scraping {market_name.upper()}...")

    categories = getCategoriesSlug(
        url_market,
        **cat_params,
        market_name=market_name,
    )

    if DEBUG_ONE_CATEGORY:
        categories = {c for c in categories if DEBUG_CATEGORY_NAME.lower() in str(c).lower()}
        if not categories:
            print(f"[DEBUG] No categories matched '{DEBUG_CATEGORY_NAME}'.")
            return
        print(f"[DEBUG] Scraping only categories: {categories}")

    print(f"Categories to scrape: {len(categories)}")

    all_products = asyncio.run(run_all_categories_async(
        url_market,
        categories,
        hash_value=COMMON_SEARCH_PARAMS["hash_value"],
        sender=COMMON_SEARCH_PARAMS["sender"],
        provider=COMMON_SEARCH_PARAMS["provider"],
        map_value="c",
        market_name=market_name,
    ))

    if all_products:
        filepath = save_market_snapshot(market_name, all_products)
        print(f"TOTAL {market_name.upper()}: {len(all_products)} products saved.")
        print(f"Saved snapshot: {filepath}")
        persist_market_online(market_name, url_market, all_products)
        refresh_latest_prices(market_name)
    else:
        print(f"TOTAL {market_name.upper()}: 0 products saved.")

    print(f"{market_name.upper()} done.\n")


def run_coto():
    url_market = "https://www.cotodigital.com.ar"
    market_name = "coto"

    print("Scraping COTO...")

    categories = get_categories_slugs_coto(url_market)

    if DEBUG_ONE_CATEGORY and categories:
        categories = [categories[0]]
        print(f"[DEBUG] Scraping only category: {categories[0]}")

    all_products = get_products_coto(url_market, categories) or []

    try:
        filepath = save_market_snapshot(market_name, all_products)
        print(f"TOTAL {market_name.upper()}: {len(all_products)} products saved.")
        print(f"Saved snapshot: {filepath}")
        persist_market_online(market_name, url_market, all_products)
        refresh_latest_prices(market_name)
    except Exception as e:
        print(f"{market_name.upper()}: failed to save snapshot - {e}")

    print("COTO done.\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run supermarket scrapers.")
    parser.add_argument(
        "supermarket",
        nargs="?",
        choices=["carrefour", "dia", "coto", "all"],
        default="all",
        help="The specific supermarket to scrape. Defaults to all.",
    )

    args = parser.parse_args()
    start_time = time.time()

    if args.supermarket in ("carrefour", "all"):
        run_vtex_market("carrefour")

    if args.supermarket in ("dia", "all"):
        run_vtex_market("dia")

    if args.supermarket in ("coto", "all"):
        run_coto()

    if args.supermarket == "all":
        print("Updating CBA for current month...")
        update_cba_current_month()

    print(f"Total time for {args.supermarket}: {round((time.time() - start_time) / 60, 2)} minutes.")

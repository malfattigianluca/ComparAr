import requests
import json

def fetch_product_detail(search_query="coca"):
    res = requests.get(f"http://127.0.0.1:8000/products/search?q={search_query}")
    data = res.json()
    if not data['results']:
        return None
    
    # Just take the first result
    first_id = data['results'][0]['id']
    print(f"Fetching detail for {first_id}")
    
    res = requests.get(f"http://127.0.0.1:8000/products/{first_id}/detail")
    detail = res.json()
    
    print("\n--- Listings ---")
    for lst in detail['all_listings']:
        print(f"Market: {lst['supermarket_code']}, Price: {lst['price_final']}, Updated: {lst['price_updated_at']}")
        
    print("\n--- History Latest ---")
    for market, hist in detail['history'].items():
        if hist:
            latest = hist[-1]
            print(f"Market: {market}, Last Scraped At: {latest['scraped_at']}, Price: {latest['price_final']}")

if __name__ == "__main__":
    fetch_product_detail("leche")
    print("\n------------------\n")
    fetch_product_detail("coca")

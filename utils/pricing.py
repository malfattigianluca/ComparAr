import re

def pos(x):
    try:
        if x is None:
            return None

        if isinstance(x, dict):
            for k in ("value", "Value", "price", "Price", "spotPrice", "SpotPrice", "ListPrice"):
                if k in x:
                    return pos(x.get(k))
            return None

        if isinstance(x, (int, float)):
            return float(x) if x > 0 else None

        if isinstance(x, str):
            s = x.strip()
            if s in ("", "0", "0.0", "0,0"):
                return None

            s = re.sub(r"[^\d.,-]", "", s)

            if s.count(",") == 1 and s.count(".") >= 1:
                s = s.replace(".", "").replace(",", ".")
            elif s.count(",") == 1 and s.count(".") == 0:
                s = s.replace(",", ".")

            v = float(s)
            return v if v > 0 else None

        return None

    except Exception:
        return None

def pick_prices(offer: dict):
    if not offer:
        return None, None

    effective_price = (
        pos(offer.get("spotPrice")) or
        pos(offer.get("Price")) or
        pos(offer.get("sellingPrice")) or
        pos(offer.get("ListPrice"))
    )
    if effective_price is None:
        return None, None

    regular_price = pos(offer.get("ListPrice")) or effective_price
    return effective_price, regular_price



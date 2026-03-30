import re

UNIT_ALIASES = {
    "lt":  ["lt", "l", "litro", "litros", "lts"],
    "ml":  ["ml", "mililitro", "mililitros"],
    "cc":  ["cc", "cm3"],
    "kg":  ["kg", "kilo", "kilos"],
    "g":   ["g", "gr", "grs", "gramo", "gramos"],
    "unit": ["unidad", "unid", "unidades", "u"]
}

def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace(",", ".")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_unit(text: str) -> str | None:
    if not text:
        return None

    text = normalize_text(text)

    for unit, aliases in UNIT_ALIASES.items():
        for alias in aliases:
            # palabra completa, no substring
            if re.search(rf"\b{alias}\b", text):
                return unit

    return None

def to_float(s: str):
    if s is None:
        return None

    s = str(s).strip()

    if re.search(r"\d+\.\d{3},\d{2}", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")

    m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else None

def safe_div(numerator, denominator):
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def parse_content(name: str):
    if not name:
        return None, None, 1

    t = (name or "").lower()
    t = t.replace(",", ".")
    t = re.sub(r"(?<=[a-záéíóúñ])(?=\d)", " ", t)
    t = re.sub(r"(?<=\d)(?=[a-záéíóúñ])", " ", t)
    t = re.sub(r"[\.]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    unit_map = {
        "g": "g", "gr": "g", "grs": "g",
        "kg": "kg",
        "ml": "ml",
        "cc": "cc",
        "l": "lt", "lt": "lt", "lts": "lt",
        "litro": "lt", "litros": "lt"
    }

    m = re.search(r"\b(\d+)\s*[xX]\s*(\d+(?:\.\d+)?)\s*(kg|g|gr|grs|ml|cc|l|lt|lts|litro|litros)\b", t)
    if m:
        n = int(m.group(1))
        per = float(m.group(2))
        unit = unit_map.get(m.group(3))
        return n * per, unit, n

    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(kg|g|gr|grs|ml|cc|l|lt|lts|litro|litros)\b", t)
    if m:
        amount = float(m.group(1))
        unit = unit_map.get(m.group(2))
        return amount, unit, 1

    return None, None, 1

def normalize_amount_unit(amount, unit):
    if amount is None or unit is None:
        return amount, unit

    unit = unit.lower()

    # volumen
    if unit == "cc":
        return amount, "ml"
    if unit in ("l", "lt"):
        return amount * 1000, "ml"

    # peso
    if unit == "kg":
        return amount * 1000, "g"
    if unit == "gr":
        return amount, "g"

    return amount, unit


/**
 * Computes a reference price (price per kg/lt/un) from a listing item.
 * Falls back to parsing the product name when price_per_unit_final is absent.
 */
export function computeRefPrice(item: {
    price_final?: number | null;
    price_per_unit_final?: number | null;
    measurement_unit?: string | null;
    name?: string | null;
}): { refPrice: number | null; refUnit: string | null } {
    if (item.price_per_unit_final) {
        return { refPrice: item.price_per_unit_final, refUnit: item.measurement_unit ?? null };
    }

    if (!item.price_final || !item.name) {
        return { refPrice: null, refUnit: null };
    }

    const m = item.name.match(/(\d+[,.]?\d*)\s*(kg|g(?:r(?:m|s)?)?|lt?s?|ml|cc|u(?:n(?:i)?)?)\.?(?:\s|$)/i);
    if (!m) return { refPrice: null, refUnit: null };

    let qty = parseFloat(m[1].replace(',', '.'));
    const u = m[2].toLowerCase();

    if (u.startsWith('g') && !u.startsWith('ga')) qty = qty / 1000;
    else if (u === 'ml' || u === 'cc') qty = qty / 1000;

    if (qty <= 0) return { refPrice: null, refUnit: null };

    const refPrice = Number(item.price_final) / qty;
    const refUnit = (u === 'ml' || u === 'cc' || u.startsWith('l')) ? 'lt'
        : (u.startsWith('g') || u === 'kg') ? 'kg'
        : 'un';

    return { refPrice, refUnit };
}

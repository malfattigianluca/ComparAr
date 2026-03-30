const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '/api');

interface SearchParams {
    q: string;
    sort_by?: string;
    markets?: string;
    page?: number;
    per_page?: number;
}

export interface SearchResponse {
    results: any[];
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
}

/**
 * Safety net para datos con encoding incorrecto almacenados antes del fix
 * del lado del scraper (forzado UTF-8 en aiohttp/requests).
 *
 * Casos cubiertos:
 * - Literales \u00XX que no fueron decodificados al persistir (Coto legacy)
 * - Mojibake UTF-8→Latin-1 (Día legacy): Ã³ → ó
 *
 * Con los scrapers corregidos, esta función no debería tener efecto en datos
 * nuevos, pero se mantiene para datos históricos ya en DB.
 */
export function fixEncoding(text: string | null): string {
    if (!text) return '';
    let fixed = text;
    // Fix literal \u00XX unicode escapes (Coto)
    fixed = fixed.replace(/\\u([0-9a-fA-F]{4})/g, (_, hex) =>
        String.fromCharCode(parseInt(hex, 16))
    );
    // Fix UTF-8→Latin-1 mojibake (Dia)
    const mojibakeMap: Record<string, string> = {
        "Ã¡": "á", "Ã©": "é", "Ã\u00ad": "í", "Ã³": "ó", "Ãº": "ú",
        "Ã±": "ñ", "Ã¼": "ü", "Ã\u0089": "É", "Ã\u0093": "Ó",
        "Âª": "ª", "Â°": "°", "Â®": "®", "Â¡": "¡", "Â¿": "¿",
    };
    for (const [bad, good] of Object.entries(mojibakeMap)) {
        fixed = fixed.split(bad).join(good);
    }
    return fixed;
}

export async function searchProducts(params: SearchParams): Promise<SearchResponse> {
    const url = new URL(`${API_BASE}/products/search`, window.location.origin);
    url.searchParams.set('q', params.q);
    if (params.sort_by) url.searchParams.set('sort_by', params.sort_by);
    if (params.markets) url.searchParams.set('markets', params.markets);
    if (params.page) url.searchParams.set('page', params.page.toString());
    if (params.per_page) url.searchParams.set('per_page', params.per_page.toString());

    const res = await fetch(url.toString());
    if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
    return res.json();
}

export async function getProductDetail(listingId: string) {
    const res = await fetch(`${API_BASE}/products/${listingId}/detail`);
    if (!res.ok) throw new Error(`Detail fetch failed: ${res.statusText}`);
    return res.json();
}

export async function getProductHistory(listingId: string) {
    const res = await fetch(`${API_BASE}/products/${listingId}/history`);
    if (!res.ok) throw new Error(`History fetch failed: ${res.statusText}`);
    return res.json();
}

export async function getCBAHistory() {
    const res = await fetch(`${API_BASE}/cba/history`);
    if (!res.ok) throw new Error(`CBA fetch failed: ${res.statusText}`);
    return res.json();
}

export async function compareCart(items: { ean: string; quantity: number }[]) {
    const res = await fetch(`${API_BASE}/compare/cart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(items),
    });
    if (!res.ok) throw new Error(`Compare failed: ${res.statusText}`);
    return res.json();
}

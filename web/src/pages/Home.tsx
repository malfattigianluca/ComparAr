import { useState, useEffect, useMemo } from 'react';
import { Search, Loader2, Filter, TrendingUp, X, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { searchProducts, getCBAHistory, fixEncoding } from '../api/client';

const MARKETS = ['coto', 'dia', 'carrefour'] as const;
const SORT_OPTIONS = [
    { value: 'price', label: 'Menor Precio' },
    { value: 'price_desc', label: 'Mayor Precio' },
    { value: 'price_per_unit', label: 'Precio x Kg/Lt' },
    { value: 'name', label: 'Alfabético' },
];

function getGenericCategory(raw: string | null, productName?: string): string {
    const c = (raw || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    const n = (productName || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');

    // ---- Carnes & Pescados (check FIRST, before Frescos) ----
    if (/bovin|carne|porc|avicol|pollo|milanesa|granja|pescad|mariscos|fiambre|embutid/.test(c)) return 'Carnes';
    if (/carnes-y-pescados/.test(c)) return 'Carnes';
    // Name-based fallback ONLY when category is generic/unknown (not snacks, almacen, etc.)
    if (!c || /^(frescos?|congelados?)$/.test(c)) {
        if (/\basado\b|\bbife\b|\bnalga\b|\bpicada\b|\bcostilla\b|\bvacio\b|\bmatambre\b|\bchorizo\b|\bmilanesa\b/.test(n)) return 'Carnes';
    }

    // ---- Lácteos ----
    if (/lacteo|leche|yogur|queso|manteca|crema|lacteos-y-productos/.test(c)) return 'Lácteos';
    if (/leche|yogur|queso|manteca/.test(n) && !/dulce de leche/.test(n)) return 'Lácteos';

    // ---- Bebidas ----
    if (/bebida|gaseosa|agua|vino|cerveza|jugo|soda|whisky|vodka|gin |aperitivo|espumante/.test(c)) return 'Bebidas';

    // ---- Verduras & Frutas ----
    if (/fruta|verdura|hortaliza|papa|cebolla|tomate|zanahoria|banana|naranja|manzana/.test(c)) return 'Frutas y Verduras';
    if (/frutas-y-verduras/.test(c)) return 'Frutas y Verduras';

    // ---- Frescos / Congelados (catch-all for "frescos" that didn't match above) ----
    if (/fresco|congelado|refrigerad/.test(c)) return 'Frescos';

    // ---- Panadería ----
    if (/panaderia|panader|reposteria|galletita|pan |dona|alfajor/.test(c)) return 'Panadería';
    if (/desayuno|merienda/.test(c)) return 'Desayuno';

    // ---- Limpieza ----
    if (/limpieza|detergente|lavandina|jabon|esponja|papel higienico|desinfectante/.test(c)) return 'Limpieza';

    // ---- Perfumería / Cuidado ----
    if (/perfumeria|cuidado|farmacia|bebe|salud|belleza|higiene|mundo-bebe/.test(c)) return 'Perfumería';

    // ---- Hogar / Bazar ----
    if (/hogar|bazar|electro|tecnolog|mascota|juguet|auto|librer|aire-libre|jardin|cuchillo|cubierto|utensilio/.test(c)) return 'Hogar';

    // ---- Almacén (default) ----
    if (/almacen|alimentos|aceite|arroz|harina|azucar|sal |snack|especialidad/.test(c)) return 'Almacén';

    return 'Otros';
}


const MARKET_COLORS: Record<string, string> = {
    coto: '#e11d48',
    dia: '#dc2626',
    carrefour: '#2563eb',
};

export default function Home() {
    const [query, setQuery] = useState('');
    const [sortBy, setSortBy] = useState('price');
    const [markets, setMarkets] = useState<string[]>([...MARKETS]);
    const [results, setResults] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [showFilters, setShowFilters] = useState(false);
    const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
    const [error, setError] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalResults, setTotalResults] = useState(0);

    // CBA
    const [cbaHistory, setCbaHistory] = useState<any[]>([]);
    const [loadingCba, setLoadingCba] = useState(true);

    useEffect(() => {
        getCBAHistory()
            .then(data => {
                if (data.history) {
                    setCbaHistory(data.history.map((h: any) => ({
                        date: new Date(h.date).toLocaleDateString('es-AR', { month: 'short', year: 'numeric' }),
                        cost: Math.round(h.min_cba * 100) / 100,
                    })));
                }
            })
            .catch(err => console.error('CBA error:', err))
            .finally(() => setLoadingCba(false));
    }, []);

    const toggleMarket = (m: string) => setMarkets(prev =>
        prev.includes(m) ? prev.filter(x => x !== m) : [...prev, m]
    );

    const doSearch = async (page = 1) => {
        if (!query || query.length < 3) return;
        if (page === 1) setSelectedCategories([]);
        setLoading(true);
        setError('');
        try {
            const data = await searchProducts({
                q: query,
                sort_by: sortBy,
                markets: markets.length > 0 ? markets.join(',') : undefined,
                page,
                per_page: 40,
            });
            // Filter out products with no price
            const withPrice = data.results.filter((r: any) => r.price_final != null);
            setResults(withPrice);
            setCurrentPage(data.page);
            setTotalPages(data.total_pages);
            setTotalResults(data.total);
        } catch (err) {
            setError('Error al buscar productos. Intenta de nuevo.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        doSearch(1);
    };

    const goToPage = (page: number) => {
        if (page < 1 || page > totalPages) return;
        doSearch(page);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const enrichedResults = useMemo(() =>
        results.map(r => ({ ...r, genericCategory: getGenericCategory(r.category, r.name) })),
        [results]
    );

    const availableCategories = useMemo(() =>
        [...new Set(enrichedResults.map(r => r.genericCategory))].sort(),
        [enrichedResults]
    );

    const filteredResults = useMemo(() =>
        selectedCategories.length > 0
            ? enrichedResults.filter(r => selectedCategories.includes(r.genericCategory))
            : enrichedResults,
        [enrichedResults, selectedCategories]
    );

    const groupedResults = useMemo(() => {
        const groups: Record<string, any> = {};
        for (const item of filteredResults) {
            const key = item.ean || item.name;
            if (!groups[key]) {
                groups[key] = { name: item.name, ean: item.ean, brand: item.brand, image_url: item.image_url, listings: [] };
            }
            groups[key].listings.push(item);
        }
        return groups;
    }, [filteredResults]);

    return (
        <div className="animate-fade-in-up">
            {/* Hero */}
            <div className="text-center py-12">
                <h1 className="text-4xl md:text-5xl font-extrabold mb-4 tracking-tight">
                    Compará y <span className="bg-gradient-to-r from-accent to-purple-400 bg-clip-text text-transparent">Ahorrá</span>
                </h1>
                <p className="text-text-secondary text-lg max-w-xl mx-auto">
                    Buscá productos en Coto, Dia y Carrefour simultáneamente para armar la canasta más barata.
                </p>
            </div>

            {/* Search */}
            <div className="glass-panel p-6 max-w-3xl mx-auto mb-12">
                <form onSubmit={handleSearch} className="flex flex-col gap-4">
                    <div className="flex gap-3">
                        <div className="relative flex-1">
                            <Search size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted" />
                            <input
                                id="search-input"
                                type="text"
                                placeholder="Ej. Coca Cola 1.5L, o código EAN"
                                className="w-full h-14 pl-12 pr-4 rounded-xl bg-black/20 border border-glass-border text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all text-base"
                                value={query}
                                onChange={e => setQuery(e.target.value)}
                            />
                        </div>
                        <button
                            type="button"
                            onClick={() => setShowFilters(!showFilters)}
                            className={`h-14 px-4 rounded-xl border transition-all cursor-pointer ${showFilters ? 'bg-accent/10 border-accent/30 text-accent' : 'bg-black/20 border-glass-border text-text-secondary hover:text-text-primary hover:border-border-hover'}`}
                        >
                            <Filter size={20} />
                        </button>
                        <button
                            type="submit"
                            id="search-button"
                            className="h-14 px-8 rounded-xl bg-accent hover:bg-accent-dark text-white font-semibold transition-all cursor-pointer hover:-translate-y-0.5 active:translate-y-0.5"
                        >
                            {loading ? <Loader2 size={22} className="animate-spin" /> : 'Buscar'}
                        </button>
                    </div>

                    {showFilters && (
                        <div className="flex flex-wrap gap-6 pt-4 border-t border-glass-border animate-fade-in-up">
                            <div className="flex flex-col gap-2">
                                <label className="text-sm text-text-secondary">Ordenar por</label>
                                <select
                                    className="px-3 py-2 rounded-lg bg-black/20 border border-glass-border text-text-primary text-sm focus:outline-none focus:border-accent"
                                    value={sortBy}
                                    onChange={e => setSortBy(e.target.value)}
                                >
                                    {SORT_OPTIONS.map(opt => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="flex flex-col gap-2">
                                <label className="text-sm text-text-secondary">Supermercados</label>
                                <div className="flex gap-3">
                                    {MARKETS.map(m => (
                                        <label key={m} className="flex items-center gap-2 cursor-pointer text-sm">
                                            <input
                                                type="checkbox"
                                                checked={markets.includes(m)}
                                                onChange={() => toggleMarket(m)}
                                                className="accent-accent"
                                            />
                                            <span className="capitalize">{m}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </form>
            </div>

            {/* Error */}
            {error && (
                <div className="glass-panel border-danger/30 p-4 max-w-3xl mx-auto mb-8 flex items-center gap-3 text-danger">
                    <X size={18} /> <span>{error}</span>
                </div>
            )}

            {/* CBA Dashboard — show only when no search results */}
            {results.length === 0 && !loading && (
                <div className="glass-panel p-6 mb-12">
                    <div className="flex items-center gap-3 mb-5">
                        <div className="bg-success/20 p-2.5 rounded-xl">
                            <TrendingUp size={22} className="text-success" />
                        </div>
                        <div>
                            <h2 className="text-lg font-semibold">Costo Canasta Básica Alimentaria</h2>
                            <p className="text-text-secondary text-sm">Evolución mensual del adulto equivalente (mínimo)</p>
                        </div>
                    </div>

                    {loadingCba ? (
                        <div className="flex justify-center py-12">
                            <Loader2 className="animate-spin text-text-muted" size={32} />
                        </div>
                    ) : cbaHistory.length > 0 ? (
                        <div className="h-72 w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={cbaHistory} margin={{ top: 5, right: 20, bottom: 5, left: 20 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" vertical={false} />
                                    <XAxis dataKey="date" stroke="#5a5a6e" tick={{ fill: '#8b8b9e', fontSize: 12 }} tickLine={false} axisLine={false} />
                                    <YAxis stroke="#5a5a6e" tick={{ fill: '#8b8b9e', fontSize: 12 }} tickLine={false} axisLine={false} tickFormatter={v => `$${v.toLocaleString('es-AR')}`} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#16161f', border: '1px solid #ffffff14', borderRadius: '12px', boxShadow: '0 8px 24px rgba(0,0,0,0.4)' }}
                                        formatter={(value: any) => [`$${Number(value || 0).toLocaleString('es-AR')}`, 'Costo Mínimo']}
                                    />
                                    <Line type="monotone" dataKey="cost" stroke="#10b981" strokeWidth={3} dot={{ fill: '#10b981', strokeWidth: 2, r: 4 }} activeDot={{ r: 6 }} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    ) : (
                        <p className="text-text-muted text-center py-8">No hay datos suficientes para calcular la CBA.</p>
                    )}
                </div>
            )}

            {/* Category Filter Pills */}
            {availableCategories.length > 1 && results.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-6">
                    {availableCategories.map(cat => (
                        <button
                            key={cat}
                            onClick={() =>
                                setSelectedCategories(prev =>
                                    prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]
                                )
                            }
                            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all cursor-pointer border ${selectedCategories.includes(cat)
                                ? 'bg-accent/15 border-accent/30 text-accent'
                                : 'bg-black/20 border-glass-border text-text-secondary hover:border-border-hover hover:text-text-primary'
                                }`}
                        >
                            {cat}
                        </button>
                    ))}
                </div>
            )}

            {/* No Results Message */}
            {!loading && results.length === 0 && query.length >= 3 && !error && (
                <div className="glass-panel p-12 text-center">
                    <Search size={48} className="mx-auto text-text-muted mb-4 opacity-40" />
                    <h3 className="text-lg font-semibold mb-2">No se encontraron resultados</h3>
                    <p className="text-text-secondary text-sm">No hay productos que coincidan con "{query}". Intentá con otro término.</p>
                </div>
            )}

            {/* Results */}
            {Object.keys(groupedResults).length > 0 && (
                <div>
                    <h3 className="text-lg font-semibold mb-6 pb-3 border-b border-glass-border">
                        {totalResults} resultados para "{query}"
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                        {Object.values(groupedResults).map((group: any, idx: number) => {
                            // Use first listing's id for the product detail link
                            const firstListingId = group.listings[0]?.id;
                            return (
                                <Link to={`/product/${firstListingId}`} key={idx} className="no-underline">
                                    <div className="glass-panel p-5 flex flex-col hover:scale-[1.01] transition-transform cursor-pointer h-full">
                                        <div className="flex gap-4 mb-4">
                                            <img
                                                src={group.image_url || 'https://via.placeholder.com/100'}
                                                alt={fixEncoding(group.name)}
                                                className="w-20 h-20 object-contain bg-white rounded-xl p-1 shrink-0"
                                                onError={e => { (e.target as HTMLImageElement).src = 'https://via.placeholder.com/100'; }}
                                            />
                                            <div className="min-w-0">
                                                <h4 className="font-semibold text-sm leading-tight line-clamp-2">{fixEncoding(group.name)}</h4>
                                                <p className="text-text-muted text-xs mt-1 truncate">{fixEncoding(group.brand)} {group.ean && `• ${group.ean}`}</p>
                                            </div>
                                        </div>

                                        <div className="mt-auto flex flex-col gap-2">
                                            {group.listings.filter((item: any) => item.price_final != null).map((item: any) => {
                                                // Compute reference price from name if not available
                                                let refPrice = item.price_per_unit_final;
                                                let refUnit = item.measurement_unit;
                                                if (!refPrice && item.price_final && item.name) {
                                                    const m = item.name.match(/(\d+[,.]?\d*)\s*(kg|g(?:r(?:m|s)?)?|lt?s?|ml|cc|u(?:n(?:i)?)?)\.?(?:\s|$)/i);
                                                    if (m) {
                                                        let qty = parseFloat(m[1].replace(',', '.'));
                                                        const u = m[2].toLowerCase();
                                                        if (u.startsWith('g') && !u.startsWith('ga')) qty = qty / 1000;
                                                        else if (u === 'ml' || u === 'cc') qty = qty / 1000;
                                                        if (qty > 0) {
                                                            refPrice = (Number(item.price_final) / qty);
                                                            refUnit = (u === 'ml' || u === 'cc' || u.startsWith('l')) ? 'lt' : (u.startsWith('g') || u === 'kg') ? 'kg' : 'un';
                                                        }
                                                    }
                                                }
                                                return (
                                                    <div key={item.id} className="flex items-center gap-1">
                                                        <Link to={`/product/${item.id}`} className="no-underline flex-1">
                                                            <div
                                                                className="flex justify-between items-center bg-black/20 p-3 rounded-xl border border-transparent hover:border-accent/30 transition-all group"
                                                            >
                                                                <div className="flex flex-col gap-1">
                                                                    <span className={`badge-${item.supermarket_code} text-xs px-2 py-0.5 rounded-full font-semibold uppercase tracking-wide inline-block w-fit`}>
                                                                        {item.supermarket_code}
                                                                    </span>
                                                                    {refPrice && (
                                                                        <span className="text-text-muted text-[11px]">
                                                                            ${Number(refPrice).toLocaleString('es-AR', { maximumFractionDigits: 0 })} x {refUnit || 'kg/lt'}
                                                                        </span>
                                                                    )}
                                                                </div>
                                                                <span className="font-bold text-base group-hover:text-accent transition-colors">
                                                                    ${Number(item.price_final).toLocaleString('es-AR')}
                                                                </span>
                                                            </div>
                                                        </Link>
                                                        {item.url_web && (
                                                            <a href={item.url_web} target="_blank" rel="noopener noreferrer" title="Ver en la tienda" className="p-2 rounded-lg hover:bg-accent/10 text-text-muted hover:text-accent transition-all shrink-0">
                                                                <ExternalLink size={14} />
                                                            </a>
                                                        )}
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                </Link>
                            );
                        })}
                    </div>

                    {/* Pagination Controls */}
                    {totalPages > 1 && (
                        <div className="flex justify-center items-center gap-2 mt-10">
                            <button
                                onClick={() => goToPage(currentPage - 1)}
                                disabled={currentPage <= 1}
                                className="px-4 py-2 rounded-xl bg-black/30 border border-glass-border text-sm font-medium disabled:opacity-30 disabled:cursor-not-allowed hover:border-accent/40 hover:text-accent transition-all cursor-pointer"
                            >
                                ← Anterior
                            </button>

                            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                                let pageNum: number;
                                if (totalPages <= 7) {
                                    pageNum = i + 1;
                                } else if (currentPage <= 4) {
                                    pageNum = i + 1;
                                } else if (currentPage >= totalPages - 3) {
                                    pageNum = totalPages - 6 + i;
                                } else {
                                    pageNum = currentPage - 3 + i;
                                }
                                return (
                                    <button
                                        key={pageNum}
                                        onClick={() => goToPage(pageNum)}
                                        className={`w-10 h-10 rounded-xl text-sm font-bold transition-all cursor-pointer border ${currentPage === pageNum
                                            ? 'bg-accent/20 border-accent/40 text-accent'
                                            : 'bg-black/20 border-glass-border text-text-secondary hover:border-border-hover'
                                            }`}
                                    >
                                        {pageNum}
                                    </button>
                                );
                            })}

                            <button
                                onClick={() => goToPage(currentPage + 1)}
                                disabled={currentPage >= totalPages}
                                className="px-4 py-2 rounded-xl bg-black/30 border border-glass-border text-sm font-medium disabled:opacity-30 disabled:cursor-not-allowed hover:border-accent/40 hover:text-accent transition-all cursor-pointer"
                            >
                                Siguiente →
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

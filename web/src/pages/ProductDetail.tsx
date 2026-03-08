import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ArrowLeft, Loader2, TrendingDown, TrendingUp, Minus, ExternalLink, Package, Tag, Barcode } from 'lucide-react';
import { getProductDetail, fixEncoding } from '../api/client';

const MARKET_INFO: Record<string, { label: string; color: string; badgeClass: string }> = {
    coto: { label: 'Coto', color: '#e11d48', badgeClass: 'badge-coto' },
    dia: { label: 'Dia', color: '#f59e0b', badgeClass: 'badge-dia' },
    carrefour: { label: 'Carrefour', color: '#2563eb', badgeClass: 'badge-carrefour' },
};

export default function ProductDetail() {
    const { id } = useParams();
    const [product, setProduct] = useState<any>(null);
    const [allListings, setAllListings] = useState<any[]>([]);
    const [history, setHistory] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!id) return;
        setLoading(true);
        getProductDetail(id)
            .then(data => {
                setProduct(data.product);
                setAllListings(data.all_listings || []);

                const chartData = (data.history || [])
                    .filter((item: any) => item.price_final != null)
                    .map((item: any) => {
                        const d = new Date(item.scraped_at);
                        return {
                            dateObj: d,
                            date: d.toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' }),
                            dateTime: d.toLocaleString('es-AR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }),
                            price: parseFloat(item.price_final),
                            priceList: item.price_list ? parseFloat(item.price_list) : null,
                        };
                    });
                setHistory(chartData);
            })
            .catch(err => {
                console.error(err);
                setError('No se pudo cargar los datos del producto.');
            })
            .finally(() => setLoading(false));
    }, [id]);

    const spansDays = history.length >= 2 &&
        history[0].dateObj?.toDateString() !== history[history.length - 1].dateObj?.toDateString();

    const priceChange = history.length >= 2
        ? ((history[history.length - 1].price - history[history.length - 2].price) / history[history.length - 2].price * 100)
        : 0;

    const currentPrice = history.length > 0 ? history[history.length - 1].price : null;
    const minPrice = history.length > 0 ? Math.min(...history.map(h => h.price)) : null;
    const maxPrice = history.length > 0 ? Math.max(...history.map(h => h.price)) : null;

    // Group listings by supermarket
    const byMarket = allListings.reduce((acc: Record<string, any[]>, item: any) => {
        const code = item.supermarket_code;
        if (!acc[code]) acc[code] = [];
        acc[code].push(item);
        return acc;
    }, {});

    // Best price across all
    const bestPrice = allListings.length > 0
        ? Math.min(...allListings.filter(l => l.price_final).map(l => Number(l.price_final)))
        : null;

    if (loading) {
        return (
            <div className="flex justify-center py-32">
                <Loader2 className="animate-spin text-accent" size={48} />
            </div>
        );
    }

    if (error) {
        return (
            <div className="animate-fade-in-up">
                <Link to="/" className="inline-flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors mb-8 no-underline text-sm">
                    <ArrowLeft size={16} /> Volver a búsqueda
                </Link>
                <p className="text-center py-12 text-danger">{error}</p>
            </div>
        );
    }

    return (
        <div className="animate-fade-in-up">
            <Link to="/" className="inline-flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors mb-8 no-underline text-sm">
                <ArrowLeft size={16} /> Volver a búsqueda
            </Link>

            {/* Product Header Card */}
            {product && (
                <div className="glass-panel p-6 mb-6">
                    <div className="flex gap-6 items-start">
                        <img
                            src={product.image_url || 'https://via.placeholder.com/160'}
                            alt={fixEncoding(product.name)}
                            className="w-32 h-32 object-contain bg-white rounded-2xl p-2 shrink-0"
                            onError={e => { (e.target as HTMLImageElement).src = 'https://via.placeholder.com/160'; }}
                        />
                        <div className="flex-1 min-w-0">
                            <h1 className="text-2xl font-bold mb-3 leading-tight">{fixEncoding(product.name)}</h1>
                            <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-text-secondary">
                                {product.brand && (
                                    <span className="flex items-center gap-1.5">
                                        <Tag size={14} className="text-accent" /> {fixEncoding(product.brand)}
                                    </span>
                                )}
                                {product.ean && (
                                    <span className="flex items-center gap-1.5">
                                        <Barcode size={14} className="text-accent" /> {product.ean}
                                    </span>
                                )}
                                {product.category && (
                                    <span className="flex items-center gap-1.5">
                                        <Package size={14} className="text-accent" /> {fixEncoding(product.category)}
                                    </span>
                                )}
                                {product.envase && (
                                    <span className="text-text-muted">{fixEncoding(product.envase)}</span>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Price Comparison Across Markets */}
            {allListings.length > 0 && (
                <div className="glass-panel p-6 mb-6">
                    <h2 className="text-lg font-bold mb-4">Comparación de Precios</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {['coto', 'dia', 'carrefour'].map(marketCode => {
                            const info = MARKET_INFO[marketCode];
                            const listings = byMarket[marketCode] || [];
                            const cheapest = listings.length > 0 ? listings[0] : null;
                            const isBest = cheapest && bestPrice !== null && Number(cheapest.price_final) === bestPrice;

                            return (
                                <div
                                    key={marketCode}
                                    className={`rounded-2xl p-5 border transition-all ${isBest
                                            ? 'bg-success/5 border-success/30'
                                            : cheapest
                                                ? 'bg-black/20 border-glass-border'
                                                : 'bg-black/10 border-glass-border opacity-50'
                                        }`}
                                >
                                    <div className="flex items-center justify-between mb-3">
                                        <span className={`${info.badgeClass} text-xs px-3 py-1 rounded-full font-semibold uppercase tracking-wide`}>
                                            {info.label}
                                        </span>
                                        {isBest && (
                                            <span className="text-[10px] bg-success/20 text-success px-2 py-0.5 rounded-full font-bold uppercase">
                                                Mejor precio
                                            </span>
                                        )}
                                    </div>

                                    {cheapest ? (
                                        <div>
                                            <p className="text-3xl font-extrabold mb-1">
                                                ${Number(cheapest.price_final).toLocaleString('es-AR')}
                                            </p>
                                            {cheapest.price_per_unit_final && (
                                                <p className="text-text-muted text-xs">
                                                    ${Number(cheapest.price_per_unit_final).toLocaleString('es-AR', { maximumFractionDigits: 0 })} x {cheapest.measurement_unit || 'kg/lt'}
                                                </p>
                                            )}
                                            {listings.length > 1 && (
                                                <p className="text-text-muted text-xs mt-1">
                                                    +{listings.length - 1} variante{listings.length > 2 ? 's' : ''}
                                                </p>
                                            )}
                                            {cheapest.url_web && (
                                                <a
                                                    href={cheapest.url_web}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="inline-flex items-center gap-1 text-xs text-accent hover:underline mt-2"
                                                >
                                                    Ver en {info.label} <ExternalLink size={11} />
                                                </a>
                                            )}
                                        </div>
                                    ) : (
                                        <p className="text-text-muted text-sm">No disponible</p>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Price History Chart */}
            <div className="glass-panel p-6">
                <h2 className="text-lg font-bold mb-4">Historial de Precios</h2>

                {/* Stats Cards */}
                {history.length > 0 && (
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                        <div className="bg-black/20 rounded-xl p-4 border border-glass-border">
                            <p className="text-text-muted text-xs uppercase tracking-wide mb-1">Precio Actual</p>
                            <p className="text-2xl font-bold">${currentPrice?.toLocaleString('es-AR')}</p>
                        </div>
                        <div className="bg-black/20 rounded-xl p-4 border border-glass-border">
                            <p className="text-text-muted text-xs uppercase tracking-wide mb-1">Variación</p>
                            <div className="flex items-center gap-2">
                                {priceChange > 0 ? <TrendingUp size={20} className="text-danger" /> :
                                    priceChange < 0 ? <TrendingDown size={20} className="text-success" /> :
                                        <Minus size={20} className="text-text-muted" />}
                                <span className={`text-2xl font-bold ${priceChange > 0 ? 'text-danger' : priceChange < 0 ? 'text-success' : 'text-text-secondary'}`}>
                                    {priceChange > 0 ? '+' : ''}{priceChange.toFixed(1)}%
                                </span>
                            </div>
                        </div>
                        <div className="bg-black/20 rounded-xl p-4 border border-glass-border">
                            <p className="text-text-muted text-xs uppercase tracking-wide mb-1">Rango</p>
                            <p className="text-lg font-bold">
                                <span className="text-success">${minPrice?.toLocaleString('es-AR')}</span>
                                <span className="text-text-muted mx-2">—</span>
                                <span className="text-danger">${maxPrice?.toLocaleString('es-AR')}</span>
                            </p>
                        </div>
                    </div>
                )}

                {history.length > 0 ? (
                    <div className="h-80 w-full">
                        <ResponsiveContainer>
                            <LineChart data={history} margin={{ top: 10, right: 30, left: 20, bottom: 20 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" />
                                <XAxis
                                    dataKey={spansDays ? 'date' : 'dateTime'}
                                    stroke="#5a5a6e"
                                    tick={{ fill: '#8b8b9e', fontSize: 11 }}
                                    interval={Math.max(0, Math.floor(history.length / 8))}
                                    angle={-30}
                                    textAnchor="end"
                                    height={60}
                                />
                                <YAxis stroke="#5a5a6e" domain={['auto', 'auto']} tick={{ fill: '#8b8b9e', fontSize: 12 }} tickFormatter={v => `$${v}`} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#16161f', border: '1px solid #ffffff14', borderRadius: '12px' }}
                                    labelFormatter={(_, payload) => {
                                        if (payload && payload[0]?.payload?.dateObj) {
                                            const d = payload[0].payload.dateObj;
                                            return d.toLocaleString('es-AR', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
                                        }
                                        return '';
                                    }}
                                    formatter={(value: any) => [`$${Number(value).toLocaleString('es-AR')}`, 'Precio']}
                                />
                                <Line type="monotone" dataKey="price" stroke="#6366f1" strokeWidth={3} activeDot={{ r: 8 }} dot={{ fill: '#0a0a0f', strokeWidth: 2 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                ) : (
                    <p className="text-center py-8 text-text-muted">No hay historial suficiente para graficar este producto.</p>
                )}
            </div>
        </div>
    );
}

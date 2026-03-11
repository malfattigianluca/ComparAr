import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ArrowLeft, Loader2, ExternalLink, Tag, Barcode, Package } from 'lucide-react';
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
    const [generalHistory, setGeneralHistory] = useState<any[]>([]);
    const [marketHistories, setMarketHistories] = useState<Record<string, any[]>>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!id) return;
        setLoading(true);
        getProductDetail(id)
            .then(data => {
                setProduct(data.product);
                setAllListings(data.all_listings || []);

                const histObj = data.history || {};
                const parsedHistories: Record<string, any[]> = {};
                const merged: Record<string, any> = {};

                for (const [market, snapshots] of Object.entries(histObj)) {
                    parsedHistories[market] = (snapshots as any[])
                        .filter((item: any) => item.price_final != null)
                        .map((item: any) => {
                            const d = new Date(item.scraped_at);
                            return {
                                dateObj: d,
                                date: d.toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' }),
                                price: parseFloat(item.price_final),
                            };
                        });

                    for (const item of parsedHistories[market]) {
                        if (!merged[item.date]) {
                            merged[item.date] = { date: item.date, dateObj: item.dateObj };
                        }
                        merged[item.date][market] = item.price;
                    }
                }
                
                setMarketHistories(parsedHistories);
                setGeneralHistory(Object.values(merged).sort((a: any, b: any) => a.dateObj.getTime() - b.dateObj.getTime()));
            })
            .catch(err => {
                console.error(err);
                setError('No se pudo cargar los datos del producto.');
            })
            .finally(() => setLoading(false));
    }, [id]);

    const getStats = (hist: any[], key: string = 'price') => {
        if (hist.length === 0) return { current: null, change: 0, min: null, max: null };
        const valid = hist.filter(h => h[key] != null);
        if (valid.length === 0) return { current: null, change: 0, min: null, max: null };
        
        const current = valid[valid.length - 1][key];
        const prev = valid.length > 1 ? valid[valid.length - 2][key] : current;
        const change = prev ? ((current - prev) / prev) * 100 : 0;
        const prices = valid.map(h => h[key]);
        
        return {
            current,
            change,
            min: Math.min(...prices),
            max: Math.max(...prices)
        };
    };

    // Calculate the most recent update across all histories
    const maxDateMs = Object.values(marketHistories).reduce((maxMs: number, hist: any[]) => {
        if (!hist || hist.length === 0) return maxMs;
        const lastItem = hist[hist.length - 1];
        if (!lastItem || !lastItem.dateObj) return maxMs;
        const ms = lastItem.dateObj.getTime();
        return ms > maxMs ? ms : maxMs;
    }, 0);

    // 48 hours in milliseconds
    const MAX_AGE_MS = 48 * 60 * 60 * 1000;

    // Filter to only include recent listings based on their market history
    const recentListings = allListings.filter((l: any) => {
        const marketCode = l.supermarket_code;
        const hist = marketHistories[marketCode];
        if (!hist || hist.length === 0) return false;
        
        const lastItem = hist[hist.length - 1];
        if (!lastItem || !lastItem.dateObj) return false;
        
        const ms = lastItem.dateObj.getTime();
        return (maxDateMs - ms) <= MAX_AGE_MS;
    });

    // Group ONLY recent listings by supermarket
    const byMarket = recentListings.reduce((acc: Record<string, any[]>, item: any) => {
        const code = item.supermarket_code;
        if (!acc[code]) acc[code] = [];
        acc[code].push(item);
        return acc;
    }, {});

    // Best price across all RECENT listings
    const bestPrice = recentListings.length > 0
        ? Math.min(...recentListings.filter((l: any) => l.price_final).map((l: any) => Number(l.price_final)))
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
                            src={product.image_url || 'https://placehold.co/160x160/16161f/8b8b9e?text=Sin+Foto'}
                            alt={fixEncoding(product.name)}
                            className="w-32 h-32 object-contain bg-white rounded-2xl p-2 shrink-0"
                            onError={e => { (e.target as HTMLImageElement).src = 'https://placehold.co/160x160/16161f/8b8b9e?text=Sin+Foto'; }}
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
            {recentListings.length > 0 && (
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

            {/* Price History Section */}
            <div className="flex flex-col gap-6">
                
                {/* General Chart (All Markets) */}
                <div className="glass-panel p-6">
                    <h2 className="text-lg font-bold mb-4">Historial General</h2>
                    {generalHistory.length > 0 ? (
                        <>
                            <div className="flex justify-end gap-4 mb-4">
                                {['coto', 'dia', 'carrefour'].map(m => MARKET_INFO[m]).map(info => (
                                    <div key={info.label} className="flex items-center gap-2 text-xs font-semibold uppercase">
                                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: info.color }}></div>
                                        {info.label}
                                    </div>
                                ))}
                            </div>
                            <div className="h-80 w-full mb-4">
                                <ResponsiveContainer>
                                    <LineChart data={generalHistory} margin={{ top: 10, right: 30, left: 20, bottom: 20 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" />
                                        <XAxis
                                            dataKey="date"
                                            stroke="#5a5a6e"
                                            tick={{ fill: '#8b8b9e', fontSize: 11 }}
                                            interval="preserveStartEnd"
                                        />
                                        <YAxis stroke="#5a5a6e" domain={['auto', 'auto']} tick={{ fill: '#8b8b9e', fontSize: 12 }} tickFormatter={v => `$${v}`} />
                                        <Tooltip
                                            contentStyle={{ backgroundColor: '#16161f', border: '1px solid #ffffff14', borderRadius: '12px' }}
                                            formatter={(value: any, name: any) => {
                                                const label = Object.values(MARKET_INFO).find(i => i.label.toLowerCase() === name)?.label || name;
                                                return [`$${Number(value).toLocaleString('es-AR')}`, label];
                                            }}
                                        />
                                        {['coto', 'dia', 'carrefour'].map(m => (
                                            <Line key={m} type="monotone" dataKey={m} name={m} stroke={MARKET_INFO[m].color} strokeWidth={3} dot={{ fill: MARKET_INFO[m].color, r: 4 }} connectNulls />
                                        ))}
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </>
                    ) : (
                        <p className="text-center py-8 text-text-muted">No hay historial suficiente para graficar este producto.</p>
                    )}
                </div>

                {/* Individual Market Charts */}
                {generalHistory.length > 0 && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {['coto', 'dia', 'carrefour'].map(marketCode => {
                            const info = MARKET_INFO[marketCode];
                            const hist = marketHistories[marketCode] || [];
                            if (hist.length === 0) return null;
                            const stats = getStats(hist, 'price');
                            
                            return (
                                <div key={marketCode} className="glass-panel p-5">
                                    <div className="flex items-center justify-between mb-4">
                                        <h3 className="font-bold flex items-center gap-2">
                                            <span className={`${info.badgeClass} w-2.5 h-2.5 rounded-full block`}></span>
                                            {info.label}
                                        </h3>
                                        <div className={`text-xs font-bold px-2 py-0.5 rounded-full ${stats.change > 0 ? 'bg-danger/10 text-danger' : stats.change < 0 ? 'bg-success/10 text-success' : 'bg-black/20 text-text-secondary'}`}>
                                            {stats.change > 0 ? '+' : ''}{stats.change.toFixed(1)}%
                                        </div>
                                    </div>
                                    <div className="flex justify-between items-end mb-4">
                                        <div>
                                            <p className="text-[10px] text-text-muted uppercase tracking-wider mb-0.5">Precio Actual</p>
                                            <p className="text-xl font-bold">${stats.current?.toLocaleString('es-AR')}</p>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-[10px] text-text-muted uppercase tracking-wider mb-0.5">Rango</p>
                                            <p className="text-sm font-semibold text-text-secondary">
                                                <span className="text-success">${stats.min?.toLocaleString('es-AR')}</span>
                                                <span className="mx-1">—</span>
                                                <span className="text-danger">${stats.max?.toLocaleString('es-AR')}</span>
                                            </p>
                                        </div>
                                    </div>
                                    <div className="h-40 w-full mt-2">
                                        <ResponsiveContainer>
                                            <LineChart data={hist} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                                                <YAxis domain={['auto', 'auto']} tick={false} axisLine={false} tickLine={false} />
                                                <Tooltip
                                                    contentStyle={{ backgroundColor: '#16161f', border: '1px solid #ffffff14', borderRadius: '8px', fontSize: '12px', padding: '4px 8px' }}
                                                    labelStyle={{ display: 'none' }}
                                                    formatter={(value: any) => [`$${Number(value).toLocaleString('es-AR')}`, '']}
                                                />
                                                <Line type="stepAfter" dataKey="price" stroke={info.color} strokeWidth={2} dot={{ fill: info.color, r: 2 }} isAnimationActive={false} />
                                            </LineChart>
                                        </ResponsiveContainer>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}

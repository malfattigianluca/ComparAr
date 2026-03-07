import React, { useState, useEffect } from 'react';
import { Search, Loader2, Filter, TrendingUp } from 'lucide-react';
import { Link } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const API_URL = 'http://localhost:8000';

const Home: React.FC = () => {
    const [query, setQuery] = useState('');
    const [sortBy, setSortBy] = useState('price');
    const [markets, setMarkets] = useState<string[]>(['coto', 'dia', 'carrefour']);
    const [results, setResults] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [showFilters, setShowFilters] = useState(false);
    const [selectedCategories, setSelectedCategories] = useState<string[]>([]);

    // CBA State
    const [cbaHistory, setCbaHistory] = useState<any[]>([]);
    const [loadingCba, setLoadingCba] = useState(true);

    useEffect(() => {
        const fetchCba = async () => {
            try {
                const res = await fetch(`${API_URL}/cba/history`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.history) {
                        const formatted = data.history.map((h: any) => ({
                            date: new Date(h.date).toLocaleDateString('es-AR', { month: 'short', year: 'numeric' }),
                            // Round the float to 2 decimals
                            cost: Math.round(h.min_cba * 100) / 100
                        }));
                        setCbaHistory(formatted);
                    }
                }
            } catch (err) {
                console.error("Failed to load CBA", err);
            } finally {
                setLoadingCba(false);
            }
        };
        fetchCba();
    }, []);

    const getGenericCategory = (rawCategory: string | null): string => {
        if (!rawCategory) return 'Otros';
        const cat = rawCategory.toLowerCase();

        if (cat.includes('bebida') || cat.includes('gaseosa') || cat.includes('agua') || cat.includes('vino') || cat.includes('cerveza') || cat.includes('licor') || cat.includes('jugo')) return 'Bebidas';
        if (cat.includes('fresco') || cat.includes('lacteo') || cat.includes('carne') || cat.includes('fruta') || cat.includes('verdura') || cat.includes('queso') || cat.includes('fiambre') || cat.includes('congelado') || cat.includes('pescaderia') || cat.includes('pollo') || cat.includes('cerdo') || cat.includes('lomo') || cat.includes('embutido')) return 'Frescos';
        if (cat.includes('limpieza') || cat.includes('detergente') || cat.includes('lavandina') || cat.includes('jabon') || cat.includes('esponja') || cat.includes('papel') || cat.includes('aromatizante') || cat.includes('aerosol') || cat.includes('vela') || cat.includes('incienso') || cat.includes('desodorante ambiente')) return 'Limpieza';
        if (cat.includes('perfumeria') || cat.includes('cuidado') || cat.includes('capilar') || cat.includes('farmacia') || cat.includes('bebe') || cat.includes('salud') || cat.includes('belleza') || cat.includes('higiene')) return 'Perfumería';
        if (cat.includes('hogar') || cat.includes('bazar') || cat.includes('textil') || cat.includes('electro') || cat.includes('tecnologia') || cat.includes('mascota') || cat.includes('ferreteria') || cat.includes('jugueteria') || cat.includes('auto') || cat.includes('libreria')) return 'Hogar y Bazar';
        return 'Almacén'; // Default fallback
    };

    const resultsWithGenericCategories = results.map(r => ({
        ...r,
        genericCategory: getGenericCategory(r.category)
    }));

    const availableCategories = Array.from(new Set(resultsWithGenericCategories.map((r: any) => r.genericCategory))).filter(Boolean).sort() as string[];

    const filteredResults = resultsWithGenericCategories.filter((item: any) => {
        if (selectedCategories.length > 0 && !selectedCategories.includes(item.genericCategory)) {
            return false;
        }
        return true;
    });

    // Group listings by EAN/Name to show standard product card containing multiple supermarket listings
    const groupedResults = filteredResults.reduce((acc, item) => {
        const key = item.ean || item.name;
        if (!acc[key]) {
            acc[key] = {
                name: item.name,
                ean: item.ean,
                brand: item.brand,
                image_url: item.image_url,
                listings: []
            };
        }
        acc[key].listings.push(item);
        return acc;
    }, {} as Record<string, any>);

    const toggleMarket = (market: string) => {
        setMarkets(prev =>
            prev.includes(market)
                ? prev.filter(m => m !== market)
                : [...prev, market]
        );
    };

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query || query.length < 3) return;

        setSelectedCategories([]);
        setLoading(true);
        try {
            const marketsQuery = markets.length > 0 ? `&markets=${markets.join(',')}` : '';
            const response = await fetch(`${API_URL}/products/search?q=${query}&sort_by=${sortBy}${marketsQuery}`);
            const data = await response.json();
            setResults(data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container animate-fade-in">
            <div style={{ textAlign: 'center', margin: '60px 0 40px' }}>
                <h1 style={{ fontSize: '3.5rem', marginBottom: '16px', fontWeight: 800 }}>
                    Compara y <span style={{ color: 'var(--accent-color)' }}>Ahorra</span>
                </h1>
                <p style={{ color: 'var(--text-muted)', fontSize: '1.2rem', maxWidth: '600px', margin: '0 auto' }}>
                    Busca productos en Coto, Dia y Carrefour simultaneamente para armar la canasta más barata.
                </p>
            </div>

            <div className="glass-panel" style={{ padding: '24px', maxWidth: '800px', margin: '0 auto 60px' }}>
                <form onSubmit={handleSearch} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div style={{ display: 'flex', gap: '16px' }}>
                        <div style={{ position: 'relative', flex: 1 }}>
                            <Search size={20} style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                            <input
                                type="text"
                                className="input-field"
                                placeholder="Ej. Coca Cola 1.5L, o codigo EAN"
                                style={{ paddingLeft: '48px', height: '56px', fontSize: '1.1rem' }}
                                value={query}
                                onChange={e => setQuery(e.target.value)}
                            />
                        </div>
                        <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => setShowFilters(!showFilters)}
                            style={{ height: '56px', padding: '0 24px' }}
                        >
                            <Filter size={20} />
                        </button>
                        <button type="submit" className="btn-primary" style={{ height: '56px', padding: '0 32px', fontSize: '1.1rem' }}>
                            {loading ? <Loader2 size={24} className="animate-spin" /> : 'Buscar'}
                        </button>
                    </div>

                    {showFilters && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '24px', paddingTop: '16px', borderTop: '1px solid var(--glass-border)' }}>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                <label style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Ordenar por:</label>
                                <select
                                    className="input-field"
                                    value={sortBy}
                                    onChange={(e) => setSortBy(e.target.value)}
                                    style={{ padding: '8px 16px' }}
                                >
                                    <option value="price">Menor Precio Final</option>
                                    <option value="price_desc">Mayor Precio Final</option>
                                    <option value="price_per_unit">Precio por Litro/Kg</option>
                                    <option value="name">Alfabético</option>
                                </select>
                            </div>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                <label style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Supermercados:</label>
                                <div style={{ display: 'flex', gap: '12px' }}>
                                    {['coto', 'dia', 'carrefour'].map(market => (
                                        <label key={market} style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                                            <input
                                                type="checkbox"
                                                checked={markets.includes(market)}
                                                onChange={() => toggleMarket(market)}
                                            />
                                            <span style={{ textTransform: 'capitalize' }}>{market}</span>
                                        </label>
                                    ))}
                                </div>
                            </div>

                            {availableCategories.length > 0 && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
                                    <label style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Categorías:</label>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', maxHeight: '150px', overflowY: 'auto', padding: '8px', background: 'rgba(0,0,0,0.1)', borderRadius: '8px' }}>
                                        {availableCategories.map(cat => (
                                            <label key={cat as string} style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                                                <input
                                                    type="checkbox"
                                                    checked={selectedCategories.includes(cat as string)}
                                                    onChange={() => {
                                                        setSelectedCategories(prev =>
                                                            prev.includes(cat as string)
                                                                ? prev.filter(c => c !== cat)
                                                                : [...prev, cat as string]
                                                        );
                                                    }}
                                                />
                                                <span style={{ textTransform: 'capitalize', fontSize: '0.85rem' }}>{(cat as string).replace(/-/g, ' ')}</span>
                                            </label>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </form>
            </div>

            {/* CBA Dashboard - Only show when NOT searching or if no results */}
            {results.length === 0 && !loading && (
                <div style={{
                    backgroundColor: '#18181b',
                    borderRadius: '16px',
                    padding: '24px',
                    marginBottom: '2rem',
                    border: '1px solid #27272a',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
                        <div style={{ backgroundColor: '#047857', padding: '10px', borderRadius: '12px' }}>
                            <TrendingUp size={24} color="white" />
                        </div>
                        <div>
                            <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>Costo Canasta Básica Alimentaria</h2>
                            <p style={{ margin: 0, color: '#a1a1aa', fontSize: '0.9rem' }}>Evolución mensual del adulto equivalente según INDEC mínimo</p>
                        </div>
                    </div>

                    {loadingCba ? (
                        <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
                            <Loader2 className="animate-spin" size={32} color="#a1a1aa" />
                        </div>
                    ) : cbaHistory.length > 0 ? (
                        <div style={{ height: '300px', width: '100%' }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={cbaHistory} margin={{ top: 5, right: 20, bottom: 5, left: 20 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                                    <XAxis
                                        dataKey="date"
                                        stroke="#a1a1aa"
                                        tick={{ fill: '#a1a1aa' }}
                                        tickLine={false}
                                        axisLine={false}
                                    />
                                    <YAxis
                                        stroke="#a1a1aa"
                                        tick={{ fill: '#a1a1aa', fontSize: '0.8rem' }}
                                        tickLine={false}
                                        axisLine={false}
                                        tickFormatter={(value) => `$${value.toLocaleString('es-AR')}`}
                                    />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '8px' }}
                                        formatter={(value: any) => [`$${Number(value || 0).toLocaleString('es-AR')}`, 'Costo Mínimo']}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="cost"
                                        stroke="#10b981"
                                        strokeWidth={3}
                                        dot={{ fill: '#10b981', strokeWidth: 2, r: 4 }}
                                        activeDot={{ r: 6 }}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    ) : (
                        <p style={{ color: '#a1a1aa', textAlign: 'center', padding: '20px' }}>No hay datos suficientes para calcular la CBA.</p>
                    )}
                </div>
            )}

            {Object.keys(groupedResults).length > 0 && (
                <div>
                    <h3 style={{ marginBottom: '24px', borderBottom: '1px solid var(--glass-border)', paddingBottom: '12px' }}>
                        Resultados para "{query}"
                    </h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '24px' }}>
                        {Object.values(groupedResults).map((group: any, idx) => (
                            <div key={idx} className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column' }}>
                                <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
                                    <img
                                        src={group.image_url || 'https://via.placeholder.com/150'}
                                        alt={group.name}
                                        style={{ width: '80px', height: '80px', objectFit: 'contain', background: '#fff', borderRadius: '8px', padding: '4px' }}
                                        onError={(e) => { (e.target as HTMLImageElement).src = 'https://via.placeholder.com/150' }}
                                    />
                                    <div>
                                        <h4 style={{ fontSize: '1rem', marginBottom: '4px' }}>{group.name}</h4>
                                        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{group.brand} | EAN: {group.ean}</p>
                                    </div>
                                </div>

                                <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                    {group.listings.map((list: any) => (
                                        <Link to={`/product/${list.id}`} key={list.id}>
                                            <div style={{
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                                alignItems: 'center',
                                                background: 'rgba(0,0,0,0.2)',
                                                padding: '12px',
                                                borderRadius: '8px',
                                                border: '1px solid transparent',
                                                transition: 'border 0.2s'
                                            }}
                                                onMouseEnter={(e) => e.currentTarget.style.borderColor = `var(--${list.supermarket_code}-color)`}
                                                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'transparent'}
                                            >
                                                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                                    <span className={`badge badge-${list.supermarket_code}`}>{list.supermarket_code}</span>
                                                    {list.price_per_unit_final && (
                                                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                                            ${list.price_per_unit_final.toLocaleString('es-AR')} x {list.measurement_unit}
                                                        </span>
                                                    )}
                                                </div>
                                                <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>
                                                    ${list.price_final ? list.price_final.toLocaleString('es-AR') : 'N/A'}
                                                </span>
                                            </div>
                                        </Link>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default Home;

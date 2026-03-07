import React, { useState } from 'react';
import { ShoppingCart, ShoppingBag, AlertCircle } from 'lucide-react';

const API_URL = 'http://localhost:8000';

const CompareCart: React.FC = () => {
    const [eansInput, setEansInput] = useState('');
    const [results, setResults] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);

    const handleCompare = async () => {
        if (!eansInput.trim()) return;

        // Parse EANs, supporting comma or newline separation
        const eans = eansInput.split(/[\s,]+/).filter(ean => ean.trim().length > 5);
        if (!eans.length) return;

        setLoading(true);
        try {
            const payload = eans.map(ean => ({ ean, quantity: 1 })); // Default qty 1
            const res = await fetch(`${API_URL}/compare/cart`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                setResults(await res.json());
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container animate-fade-in">
            <div style={{ textAlign: 'center', marginBottom: '40px' }}>
                <h2 style={{ fontSize: '2.5rem', marginBottom: '16px' }}>Comparador de Carritos</h2>
                <p style={{ color: 'var(--text-muted)' }}>Ingresa los codigos EAN de los productos para ver en qué supermercado te conviene comprar.</p>
            </div>

            <div className="glass-panel" style={{ padding: '24px', marginBottom: '40px' }}>
                <label style={{ display: 'block', marginBottom: '12px', fontWeight: 500 }}>
                    Codigos EAN (separados por coma o salto de linea)
                </label>
                <textarea
                    className="input-field"
                    style={{ minHeight: '120px', resize: 'vertical', fontFamily: 'monospace', marginBottom: '16px' }}
                    placeholder="Ej: 7790895000997, 7790040001855..."
                    value={eansInput}
                    onChange={e => setEansInput(e.target.value)}
                />
                <button className="btn-primary" style={{ width: '100%' }} onClick={handleCompare} disabled={loading}>
                    {loading ? 'Calculando...' : 'Comparar Precios Totales'}
                </button>
            </div>

            {results.length > 0 && (
                <div>
                    <h3 style={{ marginBottom: '24px' }}>Mejores opciones</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
                        {results.map((sm, i) => (
                            <div key={sm.supermarket} className="glass-panel" style={{
                                padding: '24px',
                                border: i === 0 ? '2px solid var(--accent-color)' : undefined,
                                position: 'relative',
                                overflow: 'hidden'
                            }}>
                                {i === 0 && (
                                    <div style={{
                                        position: 'absolute', top: 0, right: 0,
                                        background: 'var(--accent-color)', color: '#fff',
                                        padding: '4px 24px', fontSize: '0.8rem', fontWeight: 700,
                                        transform: 'translate(25%, 50%) rotate(45deg)',
                                        transformOrigin: 'bottom'
                                    }}>
                                        GANADOR
                                    </div>
                                )}

                                <span className={`badge badge-${sm.supermarket}`} style={{ marginBottom: '16px', fontSize: '1rem', padding: '6px 16px' }}>
                                    {sm.supermarket}
                                </span>

                                <div style={{ margin: '20px 0' }}>
                                    <div style={{ fontSize: '2.5rem', fontWeight: 800, color: i === 0 ? 'var(--accent-color)' : '#fff' }}>
                                        ${sm.total_price.toLocaleString('es-AR')}
                                    </div>
                                    <div style={{ color: 'var(--text-muted)' }}>
                                        Encontrados {sm.found_items_count} de {sm.found_items_count + sm.missing_items.length} productos
                                    </div>
                                </div>

                                {sm.missing_items.length > 0 && (
                                    <div style={{
                                        background: 'rgba(255, 171, 0, 0.1)',
                                        border: '1px solid rgba(255, 171, 0, 0.2)',
                                        padding: '12px', borderRadius: '8px', marginBottom: '20px',
                                        display: 'flex', gap: '12px', alignItems: 'flex-start'
                                    }}>
                                        <AlertCircle size={20} color="#ffab00" style={{ flexShrink: 0 }} />
                                        <div style={{ fontSize: '0.85rem', color: '#ffea9e' }}>
                                            <strong>Faltan:</strong> {sm.missing_items.join(', ')}
                                        </div>
                                    </div>
                                )}

                                <div style={{ borderTop: '1px solid var(--glass-border)', paddingTop: '16px' }}>
                                    <h4 style={{ fontSize: '0.9rem', marginBottom: '12px', color: 'var(--text-muted)' }}>Desglose:</h4>
                                    <div style={{ maxHeight: '200px', overflowY: 'auto', paddingRight: '10px' }}>
                                        {sm.items.map((item: any) => (
                                            <div key={item.ean} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.9rem', alignItems: 'center' }}>
                                                <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '180px' }} title={item.name}>
                                                    {item.quantity}x {item.name}
                                                </span>
                                                <span style={{ fontWeight: 600 }}>${item.price_total.toLocaleString('es-AR')}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <a
                                    href={`#`} // TODO: Add redirect generator to specific market
                                    className="btn-primary"
                                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', width: '100%', marginTop: '24px', padding: '12px', background: 'rgba(255,255,255,0.1)', border: '1px solid var(--glass-border)' }}
                                >
                                    <ShoppingBag size={18} /> Llenar Carrito en {sm.supermarket.toUpperCase()}
                                </a>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default CompareCart;

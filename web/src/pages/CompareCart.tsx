import { useState } from 'react';
import { ShoppingBag, AlertCircle, Loader2, Trophy } from 'lucide-react';
import { compareCart } from '../api/client';

export default function CompareCart() {
    const [eansInput, setEansInput] = useState('');
    const [results, setResults] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleCompare = async () => {
        if (!eansInput.trim()) return;
        const eans = eansInput.split(/[\s,]+/).filter(ean => ean.trim().length > 5);
        if (!eans.length) return;

        setLoading(true);
        setError('');
        try {
            const data = await compareCart(eans.map(ean => ({ ean, quantity: 1 })));
            setResults(data);
        } catch (err) {
            setError('Error al comparar. Verificá los códigos EAN e intentá de nuevo.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="animate-fade-in-up">
            <div className="text-center mb-10">
                <h2 className="text-3xl font-extrabold mb-3">Comparador de Carritos</h2>
                <p className="text-text-secondary max-w-lg mx-auto">
                    Ingresá los códigos EAN de los productos para ver en qué supermercado te conviene comprar.
                </p>
            </div>

            <div className="glass-panel p-6 mb-10 max-w-2xl mx-auto">
                <label className="block mb-3 font-medium text-sm">
                    Códigos EAN (separados por coma o salto de línea)
                </label>
                <textarea
                    id="ean-input"
                    className="w-full min-h-28 resize-y bg-black/20 border border-glass-border rounded-xl p-4 text-text-primary font-mono text-sm placeholder:text-text-muted focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all mb-4"
                    placeholder="Ej: 7790895000997, 7790040001855..."
                    value={eansInput}
                    onChange={e => setEansInput(e.target.value)}
                />
                <button
                    id="compare-button"
                    className="w-full h-12 rounded-xl bg-accent hover:bg-accent-dark text-white font-semibold transition-all cursor-pointer hover:-translate-y-0.5 active:translate-y-0.5 disabled:opacity-50"
                    onClick={handleCompare}
                    disabled={loading}
                >
                    {loading ? <Loader2 size={22} className="animate-spin mx-auto" /> : 'Comparar Precios Totales'}
                </button>
            </div>

            {error && (
                <div className="glass-panel border-danger/30 p-4 max-w-2xl mx-auto mb-8 flex items-center gap-3 text-danger">
                    <AlertCircle size={18} /> <span>{error}</span>
                </div>
            )}

            {results.length > 0 && (
                <div>
                    <h3 className="text-xl font-semibold mb-6">Resultados</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                        {results.map((sm: any, i: number) => (
                            <div
                                key={sm.supermarket}
                                className={`glass-panel p-6 relative overflow-hidden transition-all ${i === 0 ? 'border-accent/50 ring-1 ring-accent/20' : ''}`}
                            >
                                {i === 0 && (
                                    <div className="absolute top-3 right-3">
                                        <Trophy size={20} className="text-accent" />
                                    </div>
                                )}

                                <span className={`badge-${sm.supermarket} text-sm px-3 py-1 rounded-full font-semibold uppercase tracking-wide inline-block mb-4`}>
                                    {sm.supermarket}
                                </span>

                                <div className="mb-4">
                                    <div className={`text-3xl font-extrabold ${i === 0 ? 'text-accent' : ''}`}>
                                        ${sm.total_price.toLocaleString('es-AR')}
                                    </div>
                                    <div className="text-text-secondary text-sm mt-1">
                                        {sm.found_items_count} de {sm.found_items_count + sm.missing_items.length} productos encontrados
                                    </div>
                                </div>

                                {sm.missing_items.length > 0 && (
                                    <div className="bg-warning/10 border border-warning/20 rounded-xl p-3 flex gap-3 items-start mb-4 text-sm">
                                        <AlertCircle size={16} className="text-warning shrink-0 mt-0.5" />
                                        <div className="text-warning/80">
                                            <strong>Faltan:</strong> {sm.missing_items.join(', ')}
                                        </div>
                                    </div>
                                )}

                                <div className="border-t border-glass-border pt-4">
                                    <h4 className="text-xs text-text-muted uppercase tracking-wide mb-3">Desglose</h4>
                                    <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
                                        {sm.items.map((item: any) => (
                                            <div key={item.ean} className="flex justify-between text-sm items-center">
                                                <span className="truncate max-w-[180px] text-text-secondary" title={item.name}>
                                                    {item.quantity}x {item.name}
                                                </span>
                                                <span className="font-semibold ml-2">${item.price_total.toLocaleString('es-AR')}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <button className="w-full mt-5 py-3 rounded-xl bg-white/5 border border-glass-border text-text-primary hover:bg-white/10 transition-all flex items-center justify-center gap-2 text-sm font-medium cursor-pointer">
                                    <ShoppingBag size={16} /> Ir a {sm.supermarket.charAt(0).toUpperCase() + sm.supermarket.slice(1)}
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

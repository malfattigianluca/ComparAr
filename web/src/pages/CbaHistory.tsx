import { useState, useEffect } from 'react';
import { ArrowLeft, TrendingUp, TrendingDown, Minus, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { getCBAHistory } from '../api/client';

export default function CbaHistory() {
    const [history, setHistory] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        getCBAHistory()
            .then(data => {
                if (data.history) {
                    const sorted = [...data.history].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
                    setHistory(sorted.map((h: any, idx: number, arr: any[]) => {
                        const cost = Math.round(h.min_cba * 100) / 100;
                        const prevObj = arr[idx + 1];
                        const prevCost = prevObj ? Math.round(prevObj.min_cba * 100) / 100 : null;
                        const pctChange = prevCost ? ((cost - prevCost) / prevCost) * 100 : 0;
                        
                        return {
                            date: new Date(h.date).toLocaleDateString('es-AR', { month: 'long', year: 'numeric' }),
                            cost,
                            pctChange,
                            hasPrev: prevCost !== null
                        };
                    }));
                }
            })
            .catch(err => {
                console.error(err);
                setError(true);
            })
            .finally(() => setLoading(false));
    }, []);

    if (loading) {
        return (
            <div className="flex justify-center py-32">
                <Loader2 className="animate-spin text-accent" size={48} />
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-center py-12 text-danger">No se pudo cargar el historial de la CBA.</div>
        );
    }

    return (
        <div className="animate-fade-in-up max-w-4xl mx-auto">
            <Link to="/" className="inline-flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors mb-8 no-underline text-sm">
                <ArrowLeft size={16} /> Volver a búsqueda
            </Link>

            <div className="glass-panel p-8">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold mb-2">Historial Completo de CBA</h1>
                    <p className="text-text-secondary">
                        Variación del Costo de Canasta Básica Alimentaria para un Adulto Equivalente. 
                        Basado en los precios mínimos encontrados mes a mes.
                    </p>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="border-b border-glass-border">
                                <th className="py-4 px-4 text-text-muted font-semibold text-sm uppercase tracking-wider">Período</th>
                                <th className="py-4 px-4 text-text-muted font-semibold text-sm uppercase tracking-wider text-right">Costo (Individuo)</th>
                                <th className="py-4 px-4 text-text-muted font-semibold text-sm uppercase tracking-wider text-right">Costo (Familia Tipo)</th>
                                <th className="py-4 px-4 text-text-muted font-semibold text-sm uppercase tracking-wider text-right">Variación Mensual</th>
                            </tr>
                        </thead>
                        <tbody>
                            {history.map((row, idx) => (
                                <tr key={idx} className="border-b border-glass-border/50 hover:bg-black/20 transition-colors">
                                    <td className="py-4 px-4 font-medium capitalize">{row.date}</td>
                                    <td className="py-4 px-4 text-right">${row.cost.toLocaleString('es-AR', { maximumFractionDigits: 0 })}</td>
                                    <td className="py-4 px-4 text-right">${(row.cost * 3.09).toLocaleString('es-AR', { maximumFractionDigits: 0 })}</td>
                                    <td className="py-4 px-4 text-right">
                                        {!row.hasPrev ? (
                                            <span className="text-text-muted">—</span>
                                        ) : (
                                            <div className="flex items-center justify-end gap-1.5 flex-nowrap">
                                                {row.pctChange > 0 ? <TrendingUp size={16} className="text-danger" /> :
                                                 row.pctChange < 0 ? <TrendingDown size={16} className="text-success" /> :
                                                 <Minus size={16} className="text-text-muted" />}
                                                <span className={`font-bold ${row.pctChange > 0 ? 'text-danger' : row.pctChange < 0 ? 'text-success' : 'text-text-secondary'}`}>
                                                    {row.pctChange > 0 ? '+' : ''}{row.pctChange.toFixed(1)}%
                                                </span>
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

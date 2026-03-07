import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ArrowLeft, Loader2 } from 'lucide-react';

const API_URL = 'http://localhost:8000';

const ProductDetail: React.FC = () => {
    const { id } = useParams();
    const [history, setHistory] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchHistory = async () => {
            try {
                const res = await fetch(`${API_URL}/products/${id}/history`);
                if (res.ok) {
                    const data = await res.json();
                    const chartData = data
                        .filter((item: any) => item.price_final != null)
                        .map((item: any) => ({
                            date: new Date(item.scraped_at).toLocaleDateString('es-AR', { day: '2-digit', month: 'short' }),
                            price: parseFloat(item.price_final)
                        }));
                    setHistory(chartData);
                }
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchHistory();
    }, [id]);

    return (
        <div className="container animate-fade-in">
            <div style={{ marginBottom: '32px' }}>
                <Link to="/" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)' }}>
                    <ArrowLeft size={16} /> Volver a busqueda
                </Link>
            </div>

            <div className="glass-panel" style={{ padding: '32px' }}>
                <h2 style={{ marginBottom: '24px' }}>Historial de Precios</h2>

                {loading ? (
                    <div style={{ display: 'flex', justifyContent: 'center', padding: '60px' }}>
                        <Loader2 className="animate-spin" size={40} color="var(--accent-color)" />
                    </div>
                ) : history.length > 0 ? (
                    <div style={{ height: '400px', width: '100%' }}>
                        <ResponsiveContainer>
                            <LineChart data={history} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" />
                                <XAxis dataKey="date" stroke="var(--text-muted)" />
                                <YAxis stroke="var(--text-muted)" domain={['auto', 'auto']} tickFormatter={(value) => `$${value}`} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: 'var(--bg-color)', border: '1px solid var(--glass-border)', borderRadius: '8px' }}
                                    itemStyle={{ color: 'var(--accent-color)', fontWeight: 600 }}
                                    formatter={(value) => [`$${value}`, 'Precio Final']}
                                />
                                <Line
                                    type="monotone"
                                    dataKey="price"
                                    stroke="var(--accent-color)"
                                    strokeWidth={3}
                                    activeDot={{ r: 8 }}
                                    dot={{ fill: 'var(--bg-color)', strokeWidth: 2 }}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                ) : (
                    <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                        No hay historial suficiente para graficar este producto.
                    </div>
                )}
            </div>
        </div>
    );
};

export default ProductDetail;

import { useState, useEffect } from 'react';
import { getCBAHistory } from '../api/client';

export interface CbaDataPoint {
    dateObj: Date;
    date: string;
    cost: number;
}

export function useCbaHistory() {
    const [cbaHistory, setCbaHistory] = useState<CbaDataPoint[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getCBAHistory()
            .then(data => {
                if (data.history) {
                    setCbaHistory(data.history.map((h: any) => ({
                        dateObj: new Date(h.date),
                        date: new Date(h.date).toLocaleDateString('es-AR', { month: 'short', year: 'numeric' }),
                        cost: Math.round(h.min_cba * 100) / 100,
                    })));
                }
            })
            .catch(err => console.error('CBA error:', err))
            .finally(() => setLoading(false));
    }, []);

    return { cbaHistory, loading };
}

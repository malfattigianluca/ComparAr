import { Link, useLocation } from 'react-router-dom';
import { ShoppingCart, Search, BarChart3 } from 'lucide-react';

export default function Navbar() {
    const location = useLocation();

    const links = [
        { to: '/', icon: Search, label: 'Buscar' },
        { to: '/compare', icon: ShoppingCart, label: 'Mi Carrito' },
    ];

    return (
        <nav className="glass-panel mx-auto mt-4 mb-6 px-6 py-3 max-w-6xl flex items-center justify-between sticky top-4 z-50">
            <Link to="/" className="flex items-center gap-2 no-underline">
                <BarChart3 size={24} className="text-accent" />
                <span className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-accent to-purple-400 bg-clip-text text-transparent">
                    ComparAr
                </span>
            </Link>

            <div className="flex gap-6 items-center">
                {links.map(({ to, icon: Icon, label }) => (
                    <Link
                        key={to}
                        to={to}
                        className={`flex items-center gap-2 no-underline text-sm font-medium transition-colors ${location.pathname === to ? 'text-text-primary' : 'text-text-secondary hover:text-text-primary'
                            }`}
                    >
                        <Icon size={18} />
                        <span className="hidden sm:inline">{label}</span>
                    </Link>
                ))}
            </div>
        </nav>
    );
}

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ShoppingCart, Search, TrendingUp } from 'lucide-react';

const Navbar: React.FC = () => {
    const location = useLocation();

    return (
        <nav className="glass-panel" style={{
            margin: '20px auto',
            padding: '12px 24px',
            maxWidth: '1200px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            position: 'sticky',
            top: '20px',
            zIndex: 100
        }}>
            <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{
                    background: 'linear-gradient(45deg, var(--accent-color), #c258ff)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    fontSize: '1.5rem',
                    fontWeight: 800,
                    letterSpacing: '-1px'
                }}>
                    ComparAr
                </div>
            </Link>

            <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
                <Link to="/" style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    color: location.pathname === '/' ? '#fff' : 'var(--text-muted)'
                }}>
                    <Search size={18} />
                    <span style={{ fontWeight: 500 }}>Buscar</span>
                </Link>

                <Link to="/compare" style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    color: location.pathname === '/compare' ? '#fff' : 'var(--text-muted)'
                }}>
                    <ShoppingCart size={18} />
                    <span style={{ fontWeight: 500 }}>Mi Carrito</span>
                </Link>
            </div>
        </nav>
    );
};

export default Navbar;

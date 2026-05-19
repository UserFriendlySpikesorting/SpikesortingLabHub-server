import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function LoginPage() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await login(username, password);
            navigate('/dashboard');
        } catch (err) {
            setError(err.message || 'Login failed. Please check your credentials.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            minHeight: '100vh',
            background: '#f0efe8',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        }}>
            <div style={{ width: '100%', maxWidth: '360px', padding: '0 24px', boxSizing: 'border-box' }}>
                {/* Logo / brand */}
                <div style={{ textAlign: 'center', marginBottom: '40px' }}>
                    <div style={{
                        width: '48px',
                        height: '48px',
                        background: '#8fa06e',
                        borderRadius: '12px',
                        margin: '0 auto 16px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                    }}>
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.8">
                            <path d="M3 12 Q6 4 9 12 Q12 20 15 12 Q18 4 21 12"/>
                        </svg>
                    </div>
                    <h1 style={{ margin: 0, fontSize: '1.4em', fontWeight: '500', color: '#1e1e1e', letterSpacing: '-0.3px' }}>
                        LabHub
                    </h1>
                    <p style={{ margin: '6px 0 0', fontSize: '0.85em', color: '#999' }}>
                        Spike sorting pipeline manager
                    </p>
                </div>

                {/* Form card */}
                <div style={{
                    background: '#fff',
                    borderRadius: '14px',
                    padding: '32px',
                    border: '1px solid #e8e7e0',
                }}>
                    <form onSubmit={handleSubmit}>
                        <div style={{ marginBottom: '18px' }}>
                            <label style={{
                                display: 'block',
                                marginBottom: '6px',
                                color: '#555',
                                fontSize: '0.85em',
                                fontWeight: '500',
                            }}>
                                Username
                            </label>
                            <input
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="Enter your username"
                                disabled={loading}
                                style={{
                                    width: '100%',
                                    padding: '10px 12px',
                                    border: '1px solid #e0dfd8',
                                    borderRadius: '8px',
                                    fontSize: '0.9em',
                                    boxSizing: 'border-box',
                                    background: '#fafaf8',
                                    color: '#1e1e1e',
                                    outline: 'none',
                                    transition: 'border-color 0.15s',
                                }}
                                onFocus={(e) => e.target.style.borderColor = '#8fa06e'}
                                onBlur={(e) => e.target.style.borderColor = '#e0dfd8'}
                            />
                        </div>

                        <div style={{ marginBottom: '24px' }}>
                            <label style={{
                                display: 'block',
                                marginBottom: '6px',
                                color: '#555',
                                fontSize: '0.85em',
                                fontWeight: '500',
                            }}>
                                Password
                            </label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Enter your password"
                                disabled={loading}
                                style={{
                                    width: '100%',
                                    padding: '10px 12px',
                                    border: '1px solid #e0dfd8',
                                    borderRadius: '8px',
                                    fontSize: '0.9em',
                                    boxSizing: 'border-box',
                                    background: '#fafaf8',
                                    color: '#1e1e1e',
                                    outline: 'none',
                                    transition: 'border-color 0.15s',
                                }}
                                onFocus={(e) => e.target.style.borderColor = '#8fa06e'}
                                onBlur={(e) => e.target.style.borderColor = '#e0dfd8'}
                            />
                        </div>

                        {error && (
                            <div style={{
                                background: '#fef2f0',
                                color: '#c0392b',
                                padding: '10px 14px',
                                borderRadius: '8px',
                                marginBottom: '18px',
                                fontSize: '0.83em',
                                border: '1px solid #f5c6c0',
                            }}>
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            style={{
                                width: '100%',
                                padding: '11px',
                                background: loading ? '#c0c9aa' : '#8fa06e',
                                color: '#fff',
                                border: 'none',
                                borderRadius: '8px',
                                fontSize: '0.9em',
                                fontWeight: '500',
                                cursor: loading ? 'not-allowed' : 'pointer',
                                transition: 'background 0.15s',
                                letterSpacing: '0.2px',
                            }}
                            onMouseOver={(e) => !loading && (e.target.style.background = '#7d8e5e')}
                            onMouseOut={(e) => (e.target.style.background = loading ? '#c0c9aa' : '#8fa06e')}
                        >
                            {loading ? 'Signing in...' : 'Sign in'}
                        </button>
                    </form>
                </div>

                <p style={{ textAlign: 'center', marginTop: '20px', fontSize: '0.78em', color: '#bbb' }}>
                    Demo: admin / admin
                </p>
            </div>
        </div>
    );
}

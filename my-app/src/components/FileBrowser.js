import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import '../styles/FileBrowser.css';

/**
 * FileBrowser — a modal directory tree browser backed by the server.
 *
 * Props:
 *   title       {string}   Modal heading, e.g. "Select .bin file"
 *   accept      {string[]} File extensions to show, e.g. [".bin"] or [".data"]
 *   onSelect    {fn}       Called with {name, path, ext, size_mb} when user picks a file
 *   onClose     {fn}       Called when modal is dismissed
 */
export default function FileBrowser({ title, accept, onSelect, onClose }) {
    const { token } = useAuth();
    const [currentPath, setCurrentPath] = useState(null); // null = top-level roots
    const [parents, setParents] = useState([]);
    const [dirs, setDirs] = useState([]);
    const [files, setFiles] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [history, setHistory] = useState([]); // stack of previous paths for back button

    const fetchDir = useCallback((path) => {
        setLoading(true);
        setError(null);
        const url = path
            ? `/submit-jobs/browse/?path=${encodeURIComponent(path)}`
            : '/submit-jobs/browse/';
        fetch(url, {
            headers: token ? { Authorization: `Token ${token}` } : {},
            credentials: 'include',
        })
            .then((res) => {
                if (!res.ok) return res.json().then(d => { throw new Error(d.error || res.status); });
                return res.json();
            })
            .then((data) => {
                setCurrentPath(data.current_path);
                setParents(data.parents || []);
                setDirs(data.dirs || []);
                // Filter files by accepted extensions
                const filtered = (data.files || []).filter(
                    f => !accept || accept.length === 0 || accept.includes(f.ext)
                );
                setFiles(filtered);
                setLoading(false);
            })
            .catch((err) => {
                setError(err.message);
                setLoading(false);
            });
    }, [accept, token]);

    // Load root on mount
    useEffect(() => {
        fetchDir(null);
    }, [fetchDir]);

    const navigateTo = (path) => {
        setHistory(h => [...h, currentPath]);
        fetchDir(path);
    };

    const navigateBack = () => {
        if (history.length === 0) return;
        const prev = history[history.length - 1];
        setHistory(h => h.slice(0, -1));
        fetchDir(prev);
    };

    return (
        <div className="fb-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="fb-modal">
                {/* Header */}
                <div className="fb-header">
                    <span className="fb-title">{title}</span>
                    <button className="fb-close" onClick={onClose}>✕</button>
                </div>

                {/* Breadcrumb */}
                <div className="fb-breadcrumb">
                    <button
                        className="fb-crumb fb-crumb-btn"
                        onClick={() => { setHistory([]); fetchDir(null); }}
                    >
                        Roots
                    </button>
                    {parents.map((p) => (
                        <React.Fragment key={p.path}>
                            <span className="fb-crumb-sep">/</span>
                            <button className="fb-crumb fb-crumb-btn" onClick={() => navigateTo(p.path)}>
                                {p.name}
                            </button>
                        </React.Fragment>
                    ))}
                    {currentPath && (
                        <>
                            <span className="fb-crumb-sep">/</span>
                            <span className="fb-crumb fb-crumb-current">
                                {currentPath.split('/').pop()}
                            </span>
                        </>
                    )}
                </div>

                {/* Back button */}
                {history.length > 0 && (
                    <button className="fb-back-btn" onClick={navigateBack}>
                        ← Back
                    </button>
                )}

                {/* Body */}
                <div className="fb-body">
                    {loading && <div className="fb-status">Loading…</div>}
                    {error && <div className="fb-status fb-error">{error}</div>}

                    {!loading && !error && dirs.length === 0 && files.length === 0 && (
                        <div className="fb-status fb-empty">
                            No directories or matching files here.
                        </div>
                    )}

                    {/* Directories */}
                    {!loading && dirs.map((d) => (
                        <button
                            key={d.path}
                            className="fb-row fb-dir"
                            onClick={() => navigateTo(d.path)}
                        >
                            <span className="fb-icon">📁</span>
                            <span className="fb-name">{d.name}</span>
                        </button>
                    ))}

                    {/* Files */}
                    {!loading && files.map((f) => (
                        <button
                            key={f.path}
                            className="fb-row fb-file"
                            onClick={() => { onSelect(f); onClose(); }}
                        >
                            <span className="fb-icon">📄</span>
                            <span className="fb-name">{f.name}</span>
                            {f.size_mb !== null && (
                                <span className="fb-size">{f.size_mb} MB</span>
                            )}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}

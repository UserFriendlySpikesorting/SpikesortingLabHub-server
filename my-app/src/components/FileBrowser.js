import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import '../styles/FileBrowser.css';

/**
 * FileBrowser — a modal directory tree browser backed by the server.
 *
 * Props:
 *   title       {string}   Modal heading, e.g. "Select .bin file"
 *   mode        {string}   'file' (default) — pick a file, same as always.
 *                           'folder' — pick a directory instead: no files shown,
 *                           a "Select this folder" button for the folder currently
 *                           open, and a text field to name a new subfolder to
 *                           create inside it. The subfolder is not created on the
 *                           server here — the worker creates it when the job runs.
 *   accept      {string[]} (mode="file" only) Extensions to show, e.g. [".bin"]
 *   onSelect    {fn}       mode="file": called with {name, path, ext, size_mb}.
 *                           mode="folder": called with {name, path}.
 *   onClose     {fn}       Called when modal is dismissed
 */
export default function FileBrowser({ title, mode = 'file', accept, onSelect, onClose }) {
    const { token } = useAuth();
    const [currentPath, setCurrentPath] = useState(null); // null = top-level roots
    const [parents, setParents] = useState([]);
    const [dirs, setDirs] = useState([]);
    const [files, setFiles] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [history, setHistory] = useState([]); // stack of previous paths for back button
    const [newFolderName, setNewFolderName] = useState('');

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
                setNewFolderName('');
                if (mode === 'folder') {
                    setFiles([]); // folder picker never shows files
                } else {
                    // Filter files by accepted extensions
                    const filtered = (data.files || []).filter(
                        f => !accept || accept.length === 0 || accept.includes(f.ext)
                    );
                    setFiles(filtered);
                }
                setLoading(false);
            })
            .catch((err) => {
                setError(err.message);
                setLoading(false);
            });
    }, [accept, mode, token]);

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

                {/* Folder picker footer — only once inside an actual folder, not at the top-level roots */}
                {mode === 'folder' && currentPath && (
                    <div className="fb-folder-footer">
                        <button
                            className="fb-select-folder-btn"
                            onClick={() => { onSelect({ name: currentPath.split('/').pop(), path: currentPath }); onClose(); }}
                        >
                            Select this folder
                        </button>
                        <div className="fb-new-folder-row">
                            <input
                                className="fb-new-folder-input"
                                type="text"
                                placeholder="Or type a new subfolder name…"
                                value={newFolderName}
                                onChange={(e) => setNewFolderName(e.target.value)}
                            />
                            <button
                                className="fb-new-folder-btn"
                                disabled={!newFolderName.trim()}
                                onClick={() => {
                                    const name = newFolderName.trim();
                                    onSelect({ name, path: `${currentPath}/${name}` });
                                    onClose();
                                }}
                            >
                                Use this name
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

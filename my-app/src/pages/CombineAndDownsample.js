import { useState } from 'react';
import FileBrowser from '../components/FileBrowser';
import '../styles/CombineAndDownsample.css';

const MODES = [
    {
        id: 'both',
        label: 'Combine and downsample',
        description: 'Run both operations in a single pass — reads each file once, writes raw .dat and downsampled .mat simultaneously.',
        icon: (
            <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5">
                <rect x="2" y="2"   width="14" height="4" rx="1.5"/>
                <rect x="2" y="7"   width="14" height="4" rx="1.5"/>
                <rect x="2" y="12"  width="14" height="4" rx="1.5"/>
            </svg>
        ),
    },
    {
        id: 'combine',
        label: 'Combine',
        description: 'Merge multiple recordings into one continuous .dat stream. No downsampling.',
        icon: (
            <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M3 5 L9 9 L15 5"/>
                <path d="M3 9 L9 13 L15 9"/>
                <line x1="9" y1="13" x2="9" y2="16"/>
            </svg>
        ),
    },
    {
        id: 'downsample',
        label: 'Downsample',
        description: 'Reduce the sampling rate to produce an LFP-band .mat file. Input is a single combined .dat.',
        icon: (
            <svg viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5">
                <line x1="4" y1="3"  x2="4"  y2="10"/>
                <line x1="9" y1="3"  x2="9"  y2="13"/>
                <line x1="14" y1="3" x2="14" y2="7"/>
                <polyline points="2,14 9,16 16,12"/>
            </svg>
        ),
    },
];

export default function CombineAndDownsample({ onBack }) {
    const [mode, setMode]            = useState('both');
    const [inputFiles, setInputFiles] = useState([]);   // array of absolute server paths
    const [browserOpen, setBrowserOpen] = useState(false);
    const [numChannels, setChannels] = useState('64');
    const [dsFactor, setDsFactor]    = useState('30');
    const [outputName, setOutName]   = useState('');
    const [outputFolder, setOutDir]  = useState('');
    const [loading, setLoading]      = useState(false);
    const [response, setResponse]    = useState(null);  // { ok, data, error }

    function selectMode(newMode) {
        if (newMode === mode) return;
        setMode(newMode);
        setInputFiles([]);
        setResponse(null);
    }

    function handleFileSelected(f) {
        setInputFiles(prev =>
            prev.some(p => p === f.path) ? prev : [...prev, f.path]
        );
    }

    function removeFile(path) {
        setInputFiles(prev => prev.filter(p => p !== path));
    }

    function isValid() {
        if (inputFiles.length === 0) return false;
        if (!numChannels || parseInt(numChannels) < 1) return false;
        if (mode !== 'combine' && (!dsFactor || parseInt(dsFactor) < 2)) return false;
        return true;
    }

    async function handleSubmit() {
        if (!isValid()) return;
        setLoading(true);
        setResponse(null);

        try {
            const token = window.localStorage.getItem('token');

            const body = {
                input_files:       inputFiles,
                num_channels:      parseInt(numChannels),
                downsample_factor: parseInt(dsFactor),
                mode,
            };
            if (outputName.trim())   body.output_name   = outputName.trim();
            if (outputFolder.trim()) body.output_folder = outputFolder.trim();

            const resp = await fetch('/submit-jobs/combine-downsample/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Token ${token}` } : {}),
                },
                body: JSON.stringify(body),
            });

            const ct = resp.headers.get('content-type') || '';
            if (resp.ok && ct.includes('application/json')) {
                const data = await resp.json();
                setResponse({ ok: true, data });
            } else {
                const text = ct.includes('application/json')
                    ? JSON.stringify(await resp.json(), null, 2)
                    : await resp.text();
                setResponse({ ok: false, error: text });
            }
        } catch (err) {
            setResponse({ ok: false, error: err.message || String(err) });
        } finally {
            setLoading(false);
        }
    }

    const selectedMode = MODES.find(m => m.id === mode);

    return (
        <div className="cds-container">
            {/* Back */}
            <button className="cds-back" onClick={onBack}>
                <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <polyline points="10,3 5,8 10,13"/>
                </svg>
                Dashboard
            </button>

            {/* Header */}
            <div className="cds-header">
                <p className="cds-label">Pipeline</p>
                <h1>Combine &amp; Downsample</h1>
            </div>

            {/* Mode selector */}
            <div className="cds-mode-grid">
                {MODES.map(m => (
                    <div
                        key={m.id}
                        className={`cds-mode-card${mode === m.id ? ' selected' : ''}`}
                        onClick={() => selectMode(m.id)}
                    >
                        <div className="cds-mode-icon">{m.icon}</div>
                        <h3>{m.label}</h3>
                        <p>{m.description}</p>
                    </div>
                ))}
            </div>

            {/* Form */}
            <div className="cds-form">
                <p className="cds-form-title">
                    Configure — <span style={{ color: '#888', fontWeight: 400 }}>{selectedMode.label}</span>
                </p>

                {/* File picker */}
                <div className="cds-field">
                    <label>
                        Input .dat files <span style={{ color: '#e07a5a' }}>*</span>
                    </label>

                    {/* Accumulated file list */}
                    {inputFiles.length > 0 && (
                        <div className="cds-file-list">
                            {inputFiles.map((path, i) => (
                                <div key={path} className="cds-file-item">
                                    <span className="cds-file-idx">{i + 1}</span>
                                    <span className="cds-file-name" title={path}>
                                        {path.split('/').pop()}
                                    </span>
                                    <span className="cds-file-path">{path}</span>
                                    <button
                                        className="cds-file-remove"
                                        onClick={() => removeFile(path)}
                                        title="Remove"
                                    >✕</button>
                                </div>
                            ))}
                        </div>
                    )}

                    <button
                        type="button"
                        className="cds-browse-btn"
                        onClick={() => setBrowserOpen(true)}
                    >
                        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                            <path d="M2 4h4l2 2h6a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z"/>
                        </svg>
                        {inputFiles.length === 0 ? 'Browse server…' : 'Add another file…'}
                    </button>

                    {inputFiles.length > 0 && (
                        <p className="cds-hint">{inputFiles.length} file{inputFiles.length > 1 ? 's' : ''} selected. Files will be concatenated in the order listed.</p>
                    )}
                </div>

                {/* Number of channels */}
                <div className="cds-field">
                    <label>Number of channels <span style={{ color: '#e07a5a' }}>*</span></label>
                    <input
                        type="number"
                        min="1"
                        value={numChannels}
                        onChange={e => setChannels(e.target.value)}
                        placeholder="e.g. 64"
                    />
                </div>

                {/* Downsample factor — hidden for combine-only */}
                {mode !== 'combine' && (
                    <div className="cds-field">
                        <label>Downsample factor <span style={{ color: '#e07a5a' }}>*</span></label>
                        <input
                            type="number"
                            min="2"
                            value={dsFactor}
                            onChange={e => setDsFactor(e.target.value)}
                            placeholder="e.g. 30"
                        />
                        <p className="cds-hint">
                            Factor of {dsFactor || '?'} → {numChannels ? Math.round(30000 / parseInt(dsFactor || 1)) + ' Hz output' : '—'} (assuming 30 kHz input)
                        </p>
                    </div>
                )}

                <hr className="cds-divider" />

                {/* Optional fields */}
                <div className="cds-field">
                    <label>Output name <span style={{ color: '#bbb', fontWeight: 400 }}>(optional)</span></label>
                    <input
                        type="text"
                        value={outputName}
                        onChange={e => setOutName(e.target.value)}
                        placeholder="Defaults to experiment folder name"
                    />
                </div>

                <div className="cds-field">
                    <label>Output folder <span style={{ color: '#bbb', fontWeight: 400 }}>(optional)</span></label>
                    <input
                        type="text"
                        value={outputFolder}
                        onChange={e => setOutDir(e.target.value)}
                        placeholder="Defaults to combined_<experiment> next to input"
                    />
                </div>

                {/* Submit */}
                <button
                    className="cds-submit"
                    onClick={handleSubmit}
                    disabled={!isValid() || loading}
                >
                    {loading ? 'Submitting…' : `Run — ${selectedMode.label}`}
                </button>

                {/* Response */}
                {response && !response.ok && (
                    <pre className="cds-response error">{response.error}</pre>
                )}
                {response && response.ok && response.data && (
                    <div className="cds-result">
                        <p className="cds-result-op">{response.data.operation} — submitted</p>

                        <div className="cds-result-block">
                            <span className="cds-result-label">Input files</span>
                            <ul className="cds-result-list">
                                {response.data.input_files.map((f, i) => (
                                    <li key={f}>
                                        <span className="cds-result-idx">{i + 1}</span>
                                        <span className="cds-result-path">{f}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        <div className="cds-result-block">
                            <span className="cds-result-label">Output folder</span>
                            <code className="cds-result-code">{response.data.output_folder}</code>
                        </div>

                        <div className="cds-result-block">
                            <span className="cds-result-label">Output files</span>
                            <ul className="cds-result-list">
                                {response.data.output_files.map(f => (
                                    <li key={f.name}>
                                        <span className="cds-result-fname">{f.name}</span>
                                        <span className="cds-result-desc">{f.description}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                )}
            </div>

            {/* File browser modal */}
            {browserOpen && (
                <FileBrowser
                    title="Select .dat file"
                    accept={['.dat']}
                    onSelect={handleFileSelected}
                    onClose={() => setBrowserOpen(false)}
                />
            )}
        </div>
    );
}

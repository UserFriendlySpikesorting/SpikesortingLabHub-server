import React, { useState } from 'react';
import { useWizard } from '../../context/WizardContext';
import FileBrowser from '../../components/FileBrowser';
import '../../styles/WizardSteps.css';

// Convert absolute server path to $NAS$-relative path.
// Everything under the experiments/ folder is on the NAS mount.
function toNasPath(path) {
    const marker = '/experiments/';
    const idx = path.indexOf(marker);
    return idx !== -1 ? '$NAS$/' + path.slice(idx + marker.length) : path;
}

export default function StepRecording() {
    const { wizardState, updateRecording } = useWizard();
    const recording = wizardState.recording;

    // Which browser is open: null | 'bin' | 'probe'
    const [browserOpen, setBrowserOpen] = useState(null);
    const handleParameterChange = (field, value) => {
        if (field === 'numChannels') {
            const intValue = parseInt(value, 10);
            updateRecording({ [field]: isNaN(intValue) ? value : intValue });
        } else {
            const numValue = parseFloat(value);
            updateRecording({ [field]: isNaN(numValue) ? value : numValue });
        }
    };

    const handleRemoveChannelToggle = (channel) => {
        const updated = recording.removeChannels.includes(channel)
            ? recording.removeChannels.filter(c => c !== channel)
            : [...recording.removeChannels, channel];
        updateRecording({
            removeChannels: updated,
            badChannels: recording.badChannels.filter(c => !updated.includes(c)),
        });
    };

    const handleBadChannelToggle = (channel) => {
        const updated = recording.badChannels.includes(channel)
            ? recording.badChannels.filter(c => c !== channel)
            : [...recording.badChannels, channel];
        updateRecording({ badChannels: updated });
    };

    return (
        <div className="step-container recording-step">
            <h2>Step 1: Create New Recording</h2>

            <div className="recording-form">

                {/* Binfile picker */}
                <div className="form-group recording-form-group">
                    <label>Binfile (.bin / .dat / .data):</label>
                    <div className="fb-field">
                        <span className="fb-field-value" title={recording.binFile || ''}>
                            {recording.binFile
                                ? recording.binFile.split('/').pop()
                                : <span className="fb-field-placeholder">No file selected</span>}
                        </span>
                        <button
                            type="button"
                            className="fb-browse-btn"
                            onClick={() => setBrowserOpen('bin')}
                        >
                            Browse server…
                        </button>
                        {recording.binFile && (
                            <button
                                type="button"
                                className="fb-clear-btn"
                                onClick={() => updateRecording({ binFile: null })}
                                title="Clear selection"
                            >
                                ✕
                            </button>
                        )}
                    </div>
                    {recording.binFile && (
                        <div className="fb-field-path">{recording.binFile}</div>
                    )}
                </div>

                {/* Sampling Rate */}
                <div className="form-group recording-form-group">
                    <label>Sampling Rate:</label>
                    <input
                        type="number"
                        value={recording.samplingRate}
                        onChange={(e) => handleParameterChange('samplingRate', e.target.value)}
                        className="form-input recording-form-input"
                    />
                </div>

                {/* Number of Channels */}
                <div className="form-group recording-form-group">
                    <label>Number of Channels:</label>
                    <input
                        type="number"
                        value={recording.numChannels}
                        onChange={(e) => handleParameterChange('numChannels', e.target.value)}
                        className="form-input recording-form-input"
                    />
                </div>

                {/* Gain to µV */}
                <div className="form-group recording-form-group">
                    <label>Gain to µV:</label>
                    <input
                        type="number"
                        step="0.001"
                        value={recording.gainToMicroVolts}
                        onChange={(e) => handleParameterChange('gainToMicroVolts', e.target.value)}
                        className="form-input recording-form-input"
                    />
                </div>

                {/* Offset to µV */}
                <div className="form-group recording-form-group">
                    <label>Offset to µV:</label>
                    <input
                        type="number"
                        step="0.001"
                        value={recording.offsetToMicroVolts}
                        onChange={(e) => handleParameterChange('offsetToMicroVolts', e.target.value)}
                        className="form-input recording-form-input"
                    />
                </div>

                {/* Probe picker */}
                <div className="form-group recording-form-group">
                    <label>Probe file (.prb / .json):</label>
                    <div className="fb-field">
                        <span className="fb-field-value" title={recording.probeFile || ''}>
                            {recording.probeFile
                                ? recording.probeFile.split('/').pop()
                                : <span className="fb-field-placeholder">No file selected</span>}
                        </span>
                        <button
                            type="button"
                            className="fb-browse-btn"
                            onClick={() => setBrowserOpen('probe')}
                        >
                            Browse server…
                        </button>
                        {recording.probeFile && (
                            <button
                                type="button"
                                className="fb-clear-btn"
                                onClick={() => updateRecording({ probeFile: null })}
                                title="Clear selection"
                            >
                                ✕
                            </button>
                        )}
                    </div>
                    {recording.probeFile && (
                        <div className="fb-field-path">{recording.probeFile}</div>
                    )}
                </div>

                {/* Remove Channels */}
                <div className="channels-section">
                    <label className="channels-label">Remove Channels</label>
                    <div className="channels-grid">
                        {Array.from({ length: Math.max(0, recording.numChannels) }).map((_, idx) => (
                            <label key={`remove-${idx}`} className="checkbox-label">
                                <input
                                    type="checkbox"
                                    checked={recording.removeChannels.includes(idx)}
                                    onChange={() => handleRemoveChannelToggle(idx)}
                                    className="checkbox-input"
                                />
                                <span className="checkbox-text">{idx}</span>
                            </label>
                        ))}
                    </div>
                    {recording.removeChannels.length > 0 && (
                        <div className="selected-text">
                            Selected: {recording.removeChannels.join(', ')}
                        </div>
                    )}
                </div>

                {/* Bad Channels */}
                <div className="channels-section">
                    <label className="channels-label">Bad Channels</label>
                    <div className="channels-grid">
                        {Array.from({ length: Math.max(0, recording.numChannels) })
                            .map((_, idx) => idx)
                            .filter(idx => !recording.removeChannels.includes(idx))
                            .map(idx => (
                            <label key={`bad-${idx}`} className="checkbox-label">
                                <input
                                    type="checkbox"
                                    checked={recording.badChannels.includes(idx)}
                                    onChange={() => handleBadChannelToggle(idx)}
                                    className="checkbox-input"
                                />
                                <span className="checkbox-text">{idx}</span>
                            </label>
                        ))}
                    </div>
                    {recording.badChannels.length > 0 && (
                        <div className="selected-text">
                            Selected: {recording.badChannels.join(', ')}
                        </div>
                    )}
                </div>
            </div>

            {/* File browser modals */}
            {browserOpen === 'bin' && (
                <FileBrowser
                    title="Select recording file (.bin / .dat / .data)"
                    accept={['.bin', '.dat', '.data']}
                    onSelect={(f) => updateRecording({ binFile: toNasPath(f.path) })}
                    onClose={() => setBrowserOpen(null)}
                />
            )}
            {browserOpen === 'probe' && (
                <FileBrowser
                    title="Select probe file (.json)"
                    accept={['.json']}
                    onSelect={(f) => updateRecording({ probeFile: toNasPath(f.path) })}
                    onClose={() => setBrowserOpen(null)}
                />
            )}
        </div>
    );
}

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

// The raw Open Ephys file is always literally named "continuous.dat" — deriving
// a suggested name from that filename would always produce the same meaningless
// "continuous" regardless of which recording it is. A fixed, descriptive default
// is more useful than one derived from a name that carries no information here.
const SUGGESTED_OUTPUT_NAME = 'downsampled_LFP';

export default function StepDownsample() {
    const { wizardState, updateDownsample } = useWizard();
    const { recording, downsample } = wizardState;
    const [folderPickerOpen, setFolderPickerOpen] = useState(false);

    const handleToggle = () => {
        const enabling = !downsample.enabled;
        updateDownsample({
            enabled: enabling,
            // Fill in a suggested name the first time this is turned on, if empty —
            // visible and editable, never submitted without the user seeing it.
            outputName: enabling && !downsample.outputName
                ? SUGGESTED_OUTPUT_NAME
                : downsample.outputName,
        });
    };

    return (
        <div className="step-container">
            <h2>Step 2: Downsample</h2>
            <p className="step-description">
                Optionally produce a downsampled LFP file (HDF5) from the same recording, alongside sorting.
            </p>

            <div className="environment-card-single">
                <div className="environment-checkbox-group">
                    <input
                        type="checkbox"
                        id="downsample-toggle"
                        checked={downsample.enabled}
                        onChange={handleToggle}
                        className="environment-checkbox"
                    />
                    <label htmlFor="downsample-toggle" className="environment-label">
                        <div className="env-title">Downsample this recording</div>
                        <div className="env-description">
                            Reuses the recording file and channel count from Step 1 — nothing re-uploaded.
                        </div>
                    </label>
                </div>
            </div>

            {downsample.enabled && (
                <div className="recording-form">
                    {/* Reused from Step 1, read-only here */}
                    <div className="form-group recording-form-group">
                        <label>Input file (from Step 1):</label>
                        <div className="fb-field-path">
                            {recording.binFile || <span className="fb-field-placeholder">No file selected in Step 1</span>}
                        </div>
                    </div>
                    <div className="form-group recording-form-group">
                        <label>Number of channels (from Step 1):</label>
                        <div className="fb-field-path">{recording.numChannels}</div>
                    </div>

                    {/* Downsample factor */}
                    <div className="form-group recording-form-group">
                        <label>Downsample factor *:</label>
                        <input
                            type="number"
                            min="2"
                            value={downsample.downsampleFactor}
                            onChange={(e) => {
                                const v = parseInt(e.target.value, 10);
                                updateDownsample({ downsampleFactor: isNaN(v) ? e.target.value : v });
                            }}
                            className="form-input recording-form-input"
                        />
                        <div className="step-description" style={{ marginTop: '4px' }}>
                            Factor of {downsample.downsampleFactor} → {Math.round(recording.samplingRate / downsample.downsampleFactor)} Hz output
                            (assuming {recording.samplingRate} Hz input)
                        </div>
                    </div>

                    {/* Output name */}
                    <div className="form-group recording-form-group">
                        <label>Output name *:</label>
                        <input
                            type="text"
                            value={downsample.outputName}
                            onChange={(e) => updateDownsample({ outputName: e.target.value })}
                            className="form-input recording-form-input"
                        />
                    </div>

                    {/* Output folder — required, picked explicitly, never inferred */}
                    <div className="form-group recording-form-group">
                        <label>Output folder *:</label>
                        <div className="fb-field">
                            <span className="fb-field-value" title={downsample.outputFolder || ''}>
                                {downsample.outputFolder
                                    ? downsample.outputFolder.split('/').pop()
                                    : <span className="fb-field-placeholder">No folder selected</span>}
                            </span>
                            <button
                                type="button"
                                className="fb-browse-btn"
                                onClick={() => setFolderPickerOpen(true)}
                            >
                                Browse server…
                            </button>
                            {downsample.outputFolder && (
                                <button
                                    type="button"
                                    className="fb-clear-btn"
                                    onClick={() => updateDownsample({ outputFolder: '' })}
                                    title="Clear selection"
                                >
                                    ✕
                                </button>
                            )}
                        </div>
                        {downsample.outputFolder && (
                            <div className="fb-field-path">{downsample.outputFolder}</div>
                        )}
                    </div>
                </div>
            )}

            {folderPickerOpen && (
                <FileBrowser
                    title="Select output folder for downsampled LFP"
                    mode="folder"
                    onSelect={(f) => updateDownsample({ outputFolder: toNasPath(f.path) })}
                    onClose={() => setFolderPickerOpen(false)}
                />
            )}
        </div>
    );
}

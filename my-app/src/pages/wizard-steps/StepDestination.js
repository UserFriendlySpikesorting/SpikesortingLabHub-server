import React, { useState, useEffect } from 'react';
import { useWizard } from '../../context/WizardContext';
import FileBrowser from '../../components/FileBrowser';
import '../../styles/WizardSteps.css';

function toNasPath(path) {
    const marker = '/experiments/';
    const idx = path.indexOf(marker);
    return idx !== -1 ? '$NAS$/' + path.slice(idx + marker.length) : path;
}

// Whether the selected pipeline actually has an `upload` step — the only
// case where a destination is needed at all.
export function pipelineNeedsDestination(wizardState) {
    const { selectedPipeline, availablePipelines } = wizardState;
    const pipeline = availablePipelines.find(p => p.pipeline_id === selectedPipeline);
    return !!pipeline?.steps?.some(s => s.function === 'upload');
}

// Pulls "experimentN"/"recordingN" out of the Open Ephys path, e.g.
// ".../experiment1/recording2/Acquisition_Board-100.Rhythm Data/continuous.dat"
// -> "experiment1_recording2"
function extractExperimentRecording(binFile) {
    if (!binFile) return '';
    const parts = binFile.split('/');
    const experiment = parts.find(p => /^experiment\d+$/i.test(p));
    const recording = parts.find(p => /^recording\d+$/i.test(p));
    return [experiment, recording].filter(Boolean).join('_');
}

// Suggests "<pipeline_id>_experiment1_recording2" — visible and editable,
// never submitted without the user seeing it.
function suggestDestinationName(wizardState) {
    const { selectedPipeline, recording } = wizardState;
    return [selectedPipeline, extractExperimentRecording(recording.binFile)]
        .filter(Boolean)
        .join('_');
}

export default function StepDestination() {
    const { wizardState, updateDestination } = useWizard();
    const { destination } = wizardState;
    const [folderPickerOpen, setFolderPickerOpen] = useState(false);
    const needsDestination = pipelineNeedsDestination(wizardState);

    // Fill in a suggested name once, if empty — visible and editable, never
    // submitted without the user seeing it. Never overwrites what's already there.
    useEffect(() => {
        if (needsDestination && !destination.name) {
            const suggested = suggestDestinationName(wizardState);
            if (suggested) updateDestination({ name: suggested });
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [needsDestination, wizardState.selectedPipeline, wizardState.recording.binFile]);

    if (!needsDestination) {
        return (
            <div className="step-container">
                <h2>Step 5: Destination</h2>
                <div className="info-box">
                    <strong>Info:</strong> The selected pipeline has no upload step, so there's nothing to configure here.
                </div>
            </div>
        );
    }

    return (
        <div className="step-container">
            <h2>Step 5: Destination</h2>
            <p className="step-description">
                Choose where this job's results should be stored on the NAS.
            </p>

            <div className="recording-form">
                {/* Base folder — required, picked explicitly, never inferred */}
                <div className="form-group recording-form-group">
                    <label>Base folder *:</label>
                    <div className="fb-field">
                        <span className="fb-field-value" title={destination.folder || ''}>
                            {destination.folder
                                ? destination.folder.split('/').pop()
                                : <span className="fb-field-placeholder">No folder selected</span>}
                        </span>
                        <button
                            type="button"
                            className="fb-browse-btn"
                            onClick={() => setFolderPickerOpen(true)}
                        >
                            Browse server…
                        </button>
                        {destination.folder && (
                            <button
                                type="button"
                                className="fb-clear-btn"
                                onClick={() => updateDestination({ folder: '' })}
                                title="Clear selection"
                            >
                                ✕
                            </button>
                        )}
                    </div>
                    {destination.folder && (
                        <div className="fb-field-path">{destination.folder}</div>
                    )}
                </div>

                {/* Destination folder name */}
                <div className="form-group recording-form-group">
                    <label>Destination folder name *:</label>
                    <input
                        type="text"
                        value={destination.name}
                        onChange={(e) => updateDestination({ name: e.target.value })}
                        className="form-input recording-form-input"
                    />
                </div>
            </div>

            {folderPickerOpen && (
                <FileBrowser
                    title="Select destination base folder"
                    mode="folder"
                    onSelect={(f) => updateDestination({ folder: toNasPath(f.path) })}
                    onClose={() => setFolderPickerOpen(false)}
                />
            )}
        </div>
    );
}

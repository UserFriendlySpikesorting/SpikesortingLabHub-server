import React from 'react';
import { useWizard } from '../../context/WizardContext';
import '../../styles/WizardSteps.css';

export default function StepEnvironment() {
    const { wizardState, updateJobEnvironment } = useWizard();
    const { jobEnvironment } = wizardState;

    return (
        <div className="step-container">
            <h2>Step 3: Job Environment</h2>
            <p className="step-description">Select the execution environment for your job.</p>

            <div className="environment-card-single">
                <div className="environment-checkbox-group">
                    <input
                        type="checkbox"
                        id="default-env"
                        checked={jobEnvironment.preset === 'default'}
                        onChange={() => updateJobEnvironment('default')}
                        className="environment-checkbox"
                    />
                    <label htmlFor="default-env" className="environment-label">
                        <div className="env-title">Default Environment (Recommended)</div>
                        <div className="env-description">Automatically configured for optimal processing</div>
                    </label>
                </div>
            </div>

            <div className="form-section">
                <h3>Environment Configuration</h3>
                <div className="env-details">
                    <div className="detail-item">
                        <strong>Base Directory:</strong> $LOCAL$/$JOB_ID$
                    </div>
                    <div className="detail-item">
                        <strong>Number of Jobs:</strong> 40
                    </div>
                    <div className="detail-item">
                        <strong>Total Memory:</strong> 128G
                    </div>
                    <div className="detail-item">
                        <strong>Chunk Duration:</strong> 60s
                    </div>
                    <div className="detail-item">
                        <strong>Progress Bar:</strong> Enabled
                    </div>
                    <div className="detail-item">
                        <strong>Log Level:</strong> DEBUG
                    </div>
                </div>
                <div className="env-details" style={{ marginTop: '1rem' }}>
                    <h4 style={{ marginBottom: '0.5rem', fontSize: '0.95rem' }}>Output Redirects</h4>
                    <div className="detail-item">
                        <strong>Log:</strong> $NAS$/SORTING_LOGS/$JOB_ID$/run.log
                    </div>
                    <div className="detail-item">
                        <strong>Out:</strong> $NAS$/SORTING_LOGS/$JOB_ID$/run.out
                    </div>
                    <div className="detail-item">
                        <strong>Error:</strong> $NAS$/SORTING_LOGS/$JOB_ID$/run.err
                    </div>
                </div>
            </div>

            <div className="info-box">
                <strong>Info:</strong> Default Environment is automatically optimized for your recording with intelligent resource allocation
            </div>
        </div>
    );
}

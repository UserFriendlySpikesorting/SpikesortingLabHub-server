import React, { useState } from 'react';
import { useWizard } from '../../context/WizardContext';
import '../../styles/WizardSteps.css';

export default function StepReview({ onComplete }) {
    const { wizardState, resetWizard } = useWizard();
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [successData, setSuccessData] = useState(null); // { jobId, username }
    const { recording, selectedPipeline, jobEnvironment, availablePipelines } = wizardState;

    const getUsername = () => {
        try { return JSON.parse(localStorage.getItem('user'))?.username || 'User'; }
        catch { return 'User'; }
    };

    const selectedPipelineData = availablePipelines.find(p => p.pipeline_id === selectedPipeline);

    const handleSubmit = async () => {
        setIsSubmitting(true);
        setError('');

        try {
            // Check if token exists
            const token = localStorage.getItem('token');
            if (!token) {
                throw new Error('No authentication token found. Please log in first.');
            }

            // Check if pipeline is selected
            if (!selectedPipeline) {
                throw new Error('Pipeline not selected. Please go back and select a pipeline.');
            }

            // Prepare JSON payload matching backend CreateSortingJobSerializer
            const payload = {
                pipeline_id: selectedPipeline,
                recording: {
                    binfile: recording.binFile || '/local/rth/recording.dat',
                    sampling_rate: parseInt(recording.samplingRate),
                    num_channels: parseInt(recording.numChannels),
                    gain_to_uV: parseFloat(recording.gainToMicroVolts),
                    offset_to_uV: parseFloat(recording.offsetToMicroVolts),
                    probe: recording.probeFile || '/local/probes/probe.json',
                    remove_channels: recording.removeChannels.map(ch => parseInt(ch)),
                    bad_channels: recording.badChannels.map(ch => parseInt(ch)),
                },
                environment: jobEnvironment?.environment || "local"
            };

            console.log('Submitting payload:', JSON.stringify(payload, null, 2));

            const response = await fetch('/submit-jobs/create-sorting-job/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Token ${token}`,
                },
                body: JSON.stringify(payload),
            });

            console.log('Response status:', response.status);

            if (!response.ok) {
                const errorData = await response.json();
                console.error('Error response:', errorData);
                throw new Error(errorData.error || `Failed to create job (${response.status})`);
            }

            const data = await response.json();
            console.log('Success response:', data);
            setSuccessData({ jobId: data.job_id, username: getUsername() });
        } catch (err) {
            const errorMsg = err.message || 'Failed to submit job';
            setError(errorMsg);
            console.error('Error:', err);
        } finally {
            setIsSubmitting(false);
        }
    };

    if (successData) {
        return (
            <div className="sr-success-overlay">
                <div className="sr-success-card">
                    <div className="sr-success-icon">✓</div>
                    <h2 className="sr-success-title">Job Submitted</h2>
                    <p className="sr-success-sub">
                        <strong>{successData.username}</strong> submitted a new sorting job.
                    </p>
                    <div className="sr-success-id-label">Job ID</div>
                    <div className="sr-success-id">{successData.jobId}</div>
                    <button
                        className="sr-success-btn"
                        onClick={() => { resetWizard(); onComplete(); }}
                    >
                        Back to Dashboard
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="step-container">
            <h2>Step 4: Review & Submit</h2>
            <p className="step-description">Review all settings before submitting your job.</p>

            <div className="review-sections">
                {/* Recording Summary */}
                <div className="review-section">
                    <h3>Recording Configuration</h3>
                    <div className="review-items">
                        {recording.binFile && (
                            <div className="review-item">
                                <span className="label">Bin File:</span>
                                <span className="value">{recording.binFile}</span>
                            </div>
                        )}
                        {recording.probeFile && (
                            <div className="review-item">
                                <span className="label">Probe File:</span>
                                <span className="value">{recording.probeFile}</span>
                            </div>
                        )}
                        <div className="review-item">
                            <span className="label">Sampling Rate:</span>
                            <span className="value">{recording.samplingRate} Hz</span>
                        </div>
                        <div className="review-item">
                            <span className="label">Number of Channels:</span>
                            <span className="value">{recording.numChannels}</span>
                        </div>
                        <div className="review-item">
                            <span className="label">Gain to µV:</span>
                            <span className="value">{recording.gainToMicroVolts}</span>
                        </div>
                        <div className="review-item">
                            <span className="label">Offset to µV:</span>
                            <span className="value">{recording.offsetToMicroVolts}</span>
                        </div>
                        {recording.removeChannels.length > 0 && (
                            <div className="review-item">
                                <span className="label">Remove Channels:</span>
                                <span className="value">{recording.removeChannels.join(', ')}</span>
                            </div>
                        )}
                        {recording.badChannels.length > 0 && (
                            <div className="review-item">
                                <span className="label">Bad Channels:</span>
                                <span className="value">{recording.badChannels.join(', ')}</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Pipeline Summary */}
                <div className="review-section">
                    <h3>Pipeline</h3>
                    <div className="review-items">
                        <div className="review-item">
                            <span className="label">Pipeline ID:</span>
                            <span className="value">{selectedPipelineData?.pipeline_id || 'Not selected'}</span>
                        </div>
                        <div className="review-item">
                            <span className="label">Description:</span>
                            <span className="value">{selectedPipelineData?.description || '-'}</span>
                        </div>
                    </div>
                </div>

                {/* Environment Summary */}
                <div className="review-section">
                    <h3>Job Environment</h3>
                    <div className="review-items">
                        <div className="review-item">
                            <span className="label">Base Directory:</span>
                            <span className="value">$LOCAL$/$JOB_ID$</span>
                        </div>
                        <div className="review-item">
                            <span className="label">Number of Jobs:</span>
                            <span className="value">40</span>
                        </div>
                        <div className="review-item">
                            <span className="label">Total Memory:</span>
                            <span className="value">128G</span>
                        </div>
                        <div className="review-item">
                            <span className="label">Chunk Duration:</span>
                            <span className="value">60s</span>
                        </div>
                        <div className="review-item">
                            <span className="label">Progress Bar:</span>
                            <span className="value">Enabled</span>
                        </div>
                        <div className="review-item">
                            <span className="label">Log Level:</span>
                            <span className="value">DEBUG</span>
                        </div>
                    </div>
                    <div className="review-items" style={{ marginTop: '1rem' }}>
                        <h4 style={{ marginBottom: '0.5rem', fontSize: '0.95rem', fontWeight: '600' }}>Output Redirects</h4>
                        <div className="review-item">
                            <span className="label">Log:</span>
                            <span className="value">$NAS$/SORTING_LOGS/$JOB_ID$/run.log</span>
                        </div>
                        <div className="review-item">
                            <span className="label">Out:</span>
                            <span className="value">$NAS$/SORTING_LOGS/$JOB_ID$/run.out</span>
                        </div>
                        <div className="review-item">
                            <span className="label">Error:</span>
                            <span className="value">$NAS$/SORTING_LOGS/$JOB_ID$/run.err</span>
                        </div>
                    </div>
                </div>
            </div>

            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}

            <button
                className="submit-button"
                onClick={handleSubmit}
                disabled={isSubmitting}
            >
                {isSubmitting ? 'Submitting...' : 'Submit Job'}
            </button>
        </div>
    );
}

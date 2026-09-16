import React, { useEffect, useState } from 'react';
import { useWizard } from '../../context/WizardContext';
import '../../styles/WizardSteps.css';

export default function StepEnvironment() {
    const { wizardState, updateJobEnvironment, setAvailableEnvironments } = useWizard();
    const { jobEnvironment, availableEnvironments } = wizardState;
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        let cancelled = false;

        const fetchEnvironments = async () => {
            try {
                const response = await fetch('/submit-jobs/environments/', {
                    headers: {
                        'Authorization': `Token ${localStorage.getItem('token')}`,
                    },
                });

                if (!response.ok) {
                    throw new Error('Failed to fetch job environments');
                }

                const data = await response.json();
                if (cancelled) return;

                setAvailableEnvironments(data);
                if (data.length > 0) {
                    updateJobEnvironment(data[0].environment, data[0].config);
                }
            } catch (err) {
                console.error('Error fetching job environments:', err);
                if (!cancelled) {
                    setError('Could not load job environments. Please try again.');
                    setAvailableEnvironments([]);
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        };

        fetchEnvironments();
        return () => { cancelled = true; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleChange = (e) => {
        const selected = availableEnvironments.find(env => env.environment === e.target.value);
        if (selected) {
            updateJobEnvironment(selected.environment, selected.config);
        }
    };

    const config = jobEnvironment?.config;

    return (
        <div className="step-container">
            <h2>Step 3: Job Environment</h2>
            <p className="step-description">Select the execution environment for your job.</p>

            {loading && <p>Loading job environments...</p>}
            {error && <p className="error-message">{error}</p>}

            {!loading && !error && (
                <div className="form-section">
                    <label htmlFor="environment-select"><strong>Environment:</strong></label>
                    <select
                        id="environment-select"
                        value={jobEnvironment?.environment || ''}
                        onChange={handleChange}
                        className="environment-select"
                    >
                        {availableEnvironments.map(env => (
                            <option key={env.environment} value={env.environment}>
                                {env.environment === 'default'
                                    ? 'Default Environment (Recommended)'
                                    : env.environment}
                            </option>
                        ))}
                    </select>
                </div>
            )}

            {config && (
                <div className="form-section">
                    <h3>Environment Configuration</h3>
                    <div className="env-details">
                        <div className="detail-item">
                            <strong>Base Directory:</strong> {config['base directory']}
                        </div>
                        <div className="detail-item">
                            <strong>Number of Jobs:</strong> {config.job_kwargs.n_jobs}
                        </div>
                        <div className="detail-item">
                            <strong>Total Memory:</strong> {config.job_kwargs.total_memory}
                        </div>
                        <div className="detail-item">
                            <strong>Chunk Duration:</strong> {config.job_kwargs.chunk_duration}
                        </div>
                        <div className="detail-item">
                            <strong>Progress Bar:</strong> {config.job_kwargs.progress_bar ? 'Enabled' : 'Disabled'}
                        </div>
                        <div className="detail-item">
                            <strong>Log Level:</strong> {config.log_level}
                        </div>
                    </div>
                    <div className="env-details" style={{ marginTop: '1rem' }}>
                        <h4 style={{ marginBottom: '0.5rem', fontSize: '0.95rem' }}>Output Redirects</h4>
                        <div className="detail-item">
                            <strong>Log:</strong> {config.REDIRECT.log}
                        </div>
                        <div className="detail-item">
                            <strong>Out:</strong> {config.REDIRECT.out}
                        </div>
                        <div className="detail-item">
                            <strong>Error:</strong> {config.REDIRECT.err}
                        </div>
                    </div>
                </div>
            )}

            {jobEnvironment?.environment === 'default' && (
                <div className="info-box">
                    <strong>Info:</strong> Default Environment is automatically optimized for your recording with intelligent resource allocation
                </div>
            )}
        </div>
    );
}

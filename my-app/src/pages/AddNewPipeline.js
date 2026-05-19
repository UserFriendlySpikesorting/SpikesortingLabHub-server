import React, { useState } from 'react';
import '../styles/AddNewPipeline.css';

export default function AddNewPipeline({ onBack }) {
    const [jsonFile, setJsonFile] = useState(null);
    const [fileContent, setFileContent] = useState(null);
    const [description, setDescription] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [successData, setSuccessData] = useState(null); // { pipelineId, username }
    const [fileValidationError, setFileValidationError] = useState('');

    const getUsername = () => {
        try { return JSON.parse(localStorage.getItem('user'))?.username || 'User'; }
        catch { return 'User'; }
    };

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setJsonFile(file);
        setFileValidationError('');
        setError('');

        // Read the file
        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                const content = JSON.parse(event.target.result);
                setFileContent(content);
                setFileValidationError('');
            } catch (err) {
                setFileValidationError(`Invalid JSON: ${err.message}`);
                setFileContent(null);
            }
        };
        reader.readAsText(file);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccessData(null);

        if (!fileContent) {
            setError('Please select and validate a JSON file first');
            return;
        }

        if (!description.trim()) {
            setError('Please enter a description for the pipeline');
            return;
        }

        setIsSubmitting(true);

        try {
            const token = localStorage.getItem('token');
            if (!token) {
                throw new Error('No authentication token found. Please log in first.');
            }

            // Send the entire JSON content to the backend
            const response = await fetch('/pipeline-factory/pipelines/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Token ${token}`,
                },
                body: JSON.stringify({ ...fileContent, description: description.trim() }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to create pipeline');
            }

            const data = await response.json();
            setSuccessData({ pipelineId: data.pipeline_id, username: getUsername() });
        } catch (err) {
            setError(err.message || 'Failed to create pipeline');
            console.error('Error:', err);
        } finally {
            setIsSubmitting(false);
        }
    };

    if (successData) {
        return (
            <div className="pipeline-form-container">
                <div className="anp-success-overlay">
                    <div className="anp-success-card">
                        <div className="anp-success-icon">✓</div>
                        <h2 className="anp-success-title">Pipeline Created</h2>
                        <p className="anp-success-sub">
                            <strong>{successData.username}</strong> created a new pipeline.
                        </p>
                        <div className="anp-success-id-label">Pipeline ID</div>
                        <div className="anp-success-id">{successData.pipelineId}</div>
                        <button className="anp-success-btn" onClick={onBack}>
                            Back to Dashboard
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="pipeline-form-container">
            <div className="pipeline-form-header">
                <button className="back-btn" onClick={onBack}>← Back</button>
                <h1>Create New Pipeline from JSON</h1>
                <p className="subtitle">Upload a JSON file to create a new pipeline configuration</p>
            </div>

            <form onSubmit={handleSubmit} className="pipeline-form">
                {/* Description */}
                <div className="form-section">
                    <h3>Pipeline Description</h3>
                    <textarea
                        className="pipeline-description-input"
                        placeholder="Enter a description for this pipeline..."
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        rows={3}
                    />
                </div>

                {/* JSON File Upload */}
                <div className="form-section json-upload-section">
                    <h3>Upload Pipeline JSON</h3>
                    <p className="section-description">
                        Select a JSON file that contains your pipeline configuration with steps and their dependencies.
                    </p>

                    <div className="file-upload-box">
                        <input
                            type="file"
                            id="json-file-input"
                            accept=".json"
                            onChange={handleFileChange}
                            className="file-input"
                        />
                        <label htmlFor="json-file-input" className="file-label">
                            <div className="file-icon">
                                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#aaa" strokeWidth="1.5">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                                    <polyline points="14 2 14 8 20 8"/>
                                </svg>
                            </div>
                            <div className="file-text">
                                {jsonFile ? (
                                    <>
                                        <strong>Selected: {jsonFile.name}</strong>
                                        <br />
                                        <small>Click to change file</small>
                                    </>
                                ) : (
                                    <>
                                        <strong>Choose JSON file or drag and drop</strong>
                                        <br />
                                        <small>.json format required</small>
                                    </>
                                )}
                            </div>
                        </label>
                    </div>

                    {/* File Validation Status */}
                    {fileValidationError && (
                        <div className="error-message validation-error">
                            {fileValidationError}
                        </div>
                    )}

                    {fileContent && (
                        <div className="success-message validation-success">
                            File is valid
                        </div>
                    )}
                </div>

                {/* Messages */}
                {error && <div className="error-message">{error}</div>}

                {/* Submit Button */}
                <div className="form-actions">
                    <button
                        type="submit"
                        className="submit-btn"
                        disabled={isSubmitting || !fileContent}
                    >
                        {isSubmitting ? 'Creating Pipeline...' : 'Create Pipeline'}
                    </button>
                </div>
            </form>
        </div>
    );
}

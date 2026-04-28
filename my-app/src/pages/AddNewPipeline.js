import React, { useState } from 'react';
import '../styles/AddNewPipeline.css';

export default function AddNewPipeline({ onBack }) {
    const [jsonFile, setJsonFile] = useState(null);
    const [fileContent, setFileContent] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [fileValidationError, setFileValidationError] = useState('');

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
        setSuccess('');

        if (!fileContent) {
            setError('Please select and validate a JSON file first');
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
                body: JSON.stringify(fileContent),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to create pipeline');
            }

            const data = await response.json();
            setSuccess(`Pipeline created successfully. Pipeline ID: ${data.pipeline_id}`);

            // Reset form after success
            setTimeout(() => {
                setJsonFile(null);
                setFileContent(null);
                setFileValidationError('');
                document.getElementById('json-file-input').value = '';
            }, 2000);
        } catch (err) {
            setError(err.message || 'Failed to create pipeline');
            console.error('Error:', err);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="pipeline-form-container">
            <div className="pipeline-form-header">
                <button className="back-btn" onClick={onBack}>← Back</button>
                <h1>Create New Pipeline from JSON</h1>
                <p className="subtitle">Upload a JSON file to create a new pipeline configuration</p>
            </div>

            <form onSubmit={handleSubmit} className="pipeline-form">
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
                {success && <div className="success-message">{success}</div>}

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

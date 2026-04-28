import React from 'react';
import { useWizard } from '../../context/WizardContext';
import '../../styles/WizardSteps.css';

export default function StepPipeline() {
    const { wizardState, updateSelectedPipeline } = useWizard();
    const { availablePipelines, selectedPipeline } = wizardState;

    const handleSelectPipeline = (pipelineId) => {
        updateSelectedPipeline(pipelineId);
    };

    return (
        <div className="step-container">
            <h2>Step 2: Apply Pipeline</h2>
            <p className="step-description">Select a processing pipeline for your recording.</p>

            {availablePipelines.length === 0 ? (
                <div className="empty-state">
                    <p>No pipelines available. Create one in "Add New Pipeline" section.</p>
                </div>
            ) : (
                <div className="pipelines-table-wrapper">
                    <table className="pipelines-table">
                        <thead>
                            <tr>
                                <th className="checkbox-column">Select</th>
                                <th>Pipeline ID</th>
                                <th>Description</th>
                            </tr>
                        </thead>
                        <tbody>
                            {availablePipelines.map((pipeline) => (
                                <tr
                                    key={pipeline.pipeline_id}
                                    className={`pipeline-row ${selectedPipeline === pipeline.pipeline_id ? 'selected' : ''}`}
                                    onClick={() => handleSelectPipeline(pipeline.pipeline_id)}
                                >
                                    <td className="checkbox-column">
                                        <input
                                            type="checkbox"
                                            checked={selectedPipeline === pipeline.pipeline_id}
                                            onChange={() => handleSelectPipeline(pipeline.pipeline_id)}
                                            className="pipeline-checkbox"
                                        />
                                    </td>
                                    <td className="pipeline-id">#{pipeline.pipeline_id}</td>
                                    <td className="pipeline-desc">{pipeline.description}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {selectedPipeline && (
                <div className="selection-summary">
                    <strong>Selected:</strong> {availablePipelines.find(p => p.pipeline_id === selectedPipeline)?.description}
                </div>
            )}

            <div className="info-box">
                <strong>Info:</strong> The selected pipeline will process your recording with predefined steps and configurations.
            </div>
        </div>
    );
}

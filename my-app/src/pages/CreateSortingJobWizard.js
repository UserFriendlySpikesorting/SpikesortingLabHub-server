import React, { useState } from 'react';
import { useWizard } from '../context/WizardContext';
import StepRecording from './wizard-steps/StepRecording';
import StepPipeline from './wizard-steps/StepPipeline';
import StepEnvironment from './wizard-steps/StepEnvironment';
import StepReview from './wizard-steps/StepReview';
import '../styles/Wizard.css';

export default function CreateSortingJobWizard({ onBack }) {
    const [currentStep, setCurrentStep] = useState(1);
    const { wizardState, setAvailablePipelines } = useWizard();

    // Fetch pipelines on component mount
    React.useEffect(() => {
        fetchPipelines();
    }, []);

    const fetchPipelines = async () => {
        try {
            const response = await fetch('/pipeline-factory/pipelines/', {
                headers: {
                    'Authorization': `Token ${localStorage.getItem('token')}`,
                },
            });

            if (!response.ok) {
                throw new Error('Failed to fetch pipelines');
            }

            const data = await response.json();
            setAvailablePipelines(data);
        } catch (error) {
            console.error('Error fetching pipelines:', error);
            // If API fails, show empty list instead of mock data
            setAvailablePipelines([]);
        }
    };

    const handleNext = () => {
        if (validateStep(currentStep)) {
            setCurrentStep(currentStep + 1);
        }
    };

    const handlePrevious = () => {
        setCurrentStep(currentStep - 1);
    };

    const validateStep = (step) => {
        switch (step) {
            case 1:
                // Validate recording data
                if (!wizardState.recording.binFile) {
                    alert('Please upload a .bin file');
                    return false;
                }
                if (!wizardState.recording.probeFile) {
                    alert('Please upload a probe file');
                    return false;
                }
                return true;
            case 2:
                // Validate pipeline selection
                if (!wizardState.selectedPipeline) {
                    alert('Please select a pipeline');
                    return false;
                }
                return true;
            case 3:
                // Validate environment
                if (!wizardState.jobEnvironment.preset) {
                    alert('Please select a job environment');
                    return false;
                }
                return true;
            default:
                return true;
        }
    };

    return (
        <div className="wizard-container">
            <div className="wizard-header">
                <button className="back-btn" onClick={onBack}>Back</button>
                <h1>Create Sorting Job</h1>
            </div>

            {/* Progress Indicator */}
            <div className="wizard-progress">
                {[1, 2, 3, 4].map(step => (
                    <div key={step} className={`progress-step ${step <= currentStep ? 'active' : ''}`}>
                        <div className="step-number">{step}</div>
                        <div className="step-label">
                            {step === 1 && 'Recording'}
                            {step === 2 && 'Pipeline'}
                            {step === 3 && 'Environment'}
                            {step === 4 && 'Review'}
                        </div>
                    </div>
                ))}
            </div>

            {/* Step Content */}
            <div className="wizard-content">
                {currentStep === 1 && <StepRecording />}
                {currentStep === 2 && <StepPipeline />}
                {currentStep === 3 && <StepEnvironment />}
                {currentStep === 4 && <StepReview onComplete={onBack} />}
            </div>

            {/* Navigation Buttons */}
            {currentStep < 4 && (
                <div className="wizard-navigation">
                    <button
                        className="nav-button secondary"
                        onClick={handlePrevious}
                        disabled={currentStep === 1}
                    >
                        Previous
                    </button>
                    <button
                        className="nav-button primary"
                        onClick={handleNext}
                    >
                        Next
                    </button>
                </div>
            )}
        </div>
    );
}

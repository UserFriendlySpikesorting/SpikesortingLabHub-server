import React, { createContext, useContext, useState } from 'react';

const WizardContext = createContext();

export function WizardProvider({ children }) {
    const [wizardState, setWizardState] = useState({
        // Step 1: Recording
        recording: {
            binFile: null,
            probeFile: null,
            samplingRate: 30000,
            numChannels: 32,
            gainToMicroVolts: 0.195,
            offsetToMicroVolts: 0,
            removeChannels: [],
            badChannels: [],
            errors: [],
        },
        // Step 2: Pipeline
        selectedPipeline: null,
        availablePipelines: [],
        // Step 3: Environment
        jobEnvironment: {
            preset: 'default',
        },
    });

    const updateRecording = (data) => {
        setWizardState(prev => ({
            ...prev,
            recording: { ...prev.recording, ...data },
        }));
    };

    const updateSelectedPipeline = (pipelineId) => {
        setWizardState(prev => ({
            ...prev,
            selectedPipeline: pipelineId,
        }));
    };

    const updateJobEnvironment = (preset) => {
        setWizardState(prev => ({
            ...prev,
            jobEnvironment: { preset },
        }));
    };

    const setAvailablePipelines = (pipelines) => {
        setWizardState(prev => ({
            ...prev,
            availablePipelines: pipelines,
        }));
    };

    const resetWizard = () => {
        setWizardState({
            recording: {
                binFile: null,
                probeFile: null,
                samplingRate: 30000,
                numChannels: 32,
                gainToMicroVolts: 0.195,
                offsetToMicroVolts: 0,
                removeChannels: [],
                badChannels: [],
                errors: [],
            },
            selectedPipeline: null,
            availablePipelines: [],
            jobEnvironment: {
                preset: 'default',
            },
        });
    };

    const value = {
        wizardState,
        updateRecording,
        updateSelectedPipeline,
        updateJobEnvironment,
        setAvailablePipelines,
        resetWizard,
    };

    return (
        <WizardContext.Provider value={value}>
            {children}
        </WizardContext.Provider>
    );
}

export function useWizard() {
    const context = useContext(WizardContext);
    if (!context) {
        throw new Error('useWizard must be used within WizardProvider');
    }
    return context;
}

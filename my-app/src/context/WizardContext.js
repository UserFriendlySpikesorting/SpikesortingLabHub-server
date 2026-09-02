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
        // Step 2: Downsample (optional)
        downsample: {
            enabled: false,
            downsampleFactor: 30,
            outputName: '',
            outputFolder: '',
        },
        // Step 3: Pipeline
        selectedPipeline: null,
        availablePipelines: [],
        // Step 4: Environment
        jobEnvironment: {
            preset: 'default',
        },
        // Step 5: Destination (only required if the selected pipeline has an upload step)
        // Results are always moved into the destination, never left duplicated
        // in the working directory — no toggle for that here.
        destination: {
            folder: '',
            name: '',
        },
    });

    const updateRecording = (data) => {
        setWizardState(prev => ({
            ...prev,
            recording: { ...prev.recording, ...data },
        }));
    };

    const updateDownsample = (data) => {
        setWizardState(prev => ({
            ...prev,
            downsample: { ...prev.downsample, ...data },
        }));
    };

    const updateDestination = (data) => {
        setWizardState(prev => ({
            ...prev,
            destination: { ...prev.destination, ...data },
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
            downsample: {
                enabled: false,
                downsampleFactor: 30,
                outputName: '',
                outputFolder: '',
            },
            selectedPipeline: null,
            availablePipelines: [],
            jobEnvironment: {
                preset: 'default',
            },
            destination: {
                folder: '',
                name: '',
            },
        });
    };

    const value = {
        wizardState,
        updateRecording,
        updateDownsample,
        updateDestination,
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

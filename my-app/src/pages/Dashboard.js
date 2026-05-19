import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import CreateSortingJobWizard from './CreateSortingJobWizard';
import AddNewPipeline from './AddNewPipeline';
import ManageJobs from './ManageJobs';
import '../styles/Dashboard.css';

function getGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
}

export default function Dashboard() {
    const [activeSection, setActiveSection] = useState('home');
    const { user } = useAuth();

    if (activeSection === 'createJob') {
        return <CreateSortingJobWizard onBack={() => setActiveSection('home')} />;
    }

    if (activeSection === 'addPipeline') {
        return <AddNewPipeline onBack={() => setActiveSection('home')} />;
    }

    if (activeSection === 'manageJobs') {
        return <ManageJobs onBack={() => setActiveSection('home')} />;
    }

    return (
        <div className="dashboard-container">
            {/* Greeting */}
            <div className="dashboard-greeting">
                <h1>{getGreeting()}{user?.username ? `, ${user.username}` : ''}</h1>
                <p>Your spike sorting workspace is ready</p>
            </div>

            {/* Pipeline Actions */}
            <p className="section-title">Pipeline Actions</p>
            <div className="dashboard-actions">
                <div
                    className="action-card create-job"
                    onClick={() => setActiveSection('createJob')}
                >
                    <div className="card-icon-label">
                        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                            <circle cx="8" cy="8" r="6.5"/>
                            <line x1="8" y1="5" x2="8" y2="11"/>
                            <line x1="5" y1="8" x2="11" y2="8"/>
                        </svg>
                        New Job
                    </div>
                    <h3>Create Sorting Job</h3>
                    <p>Start a new spike sorting workflow with your recording data and chosen pipeline.</p>
                    <div className="card-tags">
                        <span className="card-tag">Wizard</span>
                        <span className="card-tag">Recording</span>
                        <span className="card-tag">Pipeline</span>
                    </div>
                </div>

                <div
                    className="action-card add-pipeline"
                    onClick={() => setActiveSection('addPipeline')}
                >
                    <div className="card-icon-label">
                        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                            <rect x="2" y="2" width="12" height="12" rx="2"/>
                            <line x1="8" y1="5" x2="8" y2="11"/>
                            <line x1="5" y1="8" x2="11" y2="8"/>
                        </svg>
                        Templates
                    </div>
                    <h3>Add New Pipeline</h3>
                    <p>Create a reusable pipeline template with custom processing steps and configurations.</p>
                    <div className="card-tags">
                        <span className="card-tag">Template</span>
                        <span className="card-tag">Steps</span>
                        <span className="card-tag">Reusable</span>
                    </div>
                </div>

                <div
                    className="action-card manage-jobs"
                    onClick={() => setActiveSection('manageJobs')}
                >
                    <div className="card-icon-label">
                        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                            <line x1="2" y1="4" x2="14" y2="4"/>
                            <line x1="2" y1="8" x2="14" y2="8"/>
                            <line x1="2" y1="12" x2="10" y2="12"/>
                        </svg>
                        Monitor
                    </div>
                    <h3>Manage Jobs</h3>
                    <p>Monitor and inspect your job history, track progress, and update statuses.</p>
                    <div className="card-tags">
                        <span className="card-tag">History</span>
                        <span className="card-tag">Status</span>
                        <span className="card-tag">Progress</span>
                    </div>
                </div>
            </div>

            {/* Your Workspace */}
            <div className="workspace-section">
                <p className="section-title">Your Workspace</p>
                <div className="workspace-grid">
                    <div className="workspace-card">
                        <h4>
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                                <circle cx="8" cy="8" r="6.5"/>
                                <polyline points="8,4 8,8 11,10"/>
                            </svg>
                            Recent Activity
                        </h4>
                        <p className="workspace-stat-label">Click Manage Jobs to view your recent sorting jobs and their current status.</p>
                    </div>
                    <div className="workspace-card">
                        <h4>
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                                <path d="M2 12 L6 6 L9 9 L12 5 L14 7"/>
                            </svg>
                            Quick Start
                        </h4>
                        <p className="workspace-stat-label">New here? Start by adding a pipeline template, then create your first sorting job.</p>
                    </div>
                    <div className="workspace-card">
                        <h4>
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                                <circle cx="8" cy="8" r="6.5"/>
                                <line x1="8" y1="5" x2="8" y2="8.5"/>
                                <circle cx="8" cy="11" r="0.5" fill="currentColor"/>
                            </svg>
                            Help
                        </h4>
                        <p className="workspace-stat-label">Use the wizard to configure recordings, select pipelines, and set up environments.</p>
                    </div>
                </div>
            </div>
        </div>
    );
}

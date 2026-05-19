import React, { useState, useEffect, useRef } from 'react';
import '../styles/ManageJobs.css';

const AUTO_REFRESH_INTERVAL = 10000; // 10 seconds

export default function ManageJobs({ onBack }) {
    const [jobs, setJobs] = useState([]);
    const [statistics, setStatistics] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    const [selectedJob, setSelectedJob] = useState(null);
    const [statusFilter, setStatusFilter] = useState('');
    const [lastRefreshed, setLastRefreshed] = useState(null);
    const isFetchingRef = useRef(false);

    const openJobDetail = (job) => {
        window.history.pushState({ jobDetail: true }, '');
        setSelectedJob(job);
    };

    const closeJobDetail = () => setSelectedJob(null);

    useEffect(() => {
        const handlePopState = () => { if (selectedJob) setSelectedJob(null); };
        window.addEventListener('popstate', handlePopState);
        return () => window.removeEventListener('popstate', handlePopState);
    }, [selectedJob]);

    // Keep selectedJob in sync when the jobs list refreshes
    useEffect(() => {
        if (selectedJob) {
            const updated = jobs.find(j => j.job_id === selectedJob.job_id);
            if (updated) setSelectedJob(updated);
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [jobs]);

    useEffect(() => {
        fetchJobs();
        fetchStatistics();

        const interval = setInterval(() => {
            if (!isFetchingRef.current) {
                fetchJobs();
                fetchStatistics();
            }
        }, AUTO_REFRESH_INTERVAL);

        return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [statusFilter]);

    const fetchJobs = async () => {
        isFetchingRef.current = true;
        setIsLoading(prev => jobs.length === 0 ? true : prev);
        setError('');
        try {
            const url = statusFilter
                ? `/job-queue/list/?status=${statusFilter}`
                : `/job-queue/list/`;
            const response = await fetch(url, {
                headers: { 'Authorization': `Token ${localStorage.getItem('token')}` },
            });
            if (!response.ok) throw new Error('Failed to fetch jobs');
            const data = await response.json();
            setJobs(data.jobs || []);
            setLastRefreshed(new Date());
        } catch (err) {
            setError(err.message || 'Failed to load jobs');
        } finally {
            setIsLoading(false);
            isFetchingRef.current = false;
        }
    };

    const fetchStatistics = async () => {
        try {
            const response = await fetch('/job-queue/statistics/', {
                headers: { 'Authorization': `Token ${localStorage.getItem('token')}` },
            });
            if (!response.ok) return;
            const data = await response.json();
            setStatistics(data);
        } catch (err) {
            console.error('Error fetching statistics:', err);
        }
    };

    const STATUS_COLORS = {
        completed: '#28a745',
        running:   '#2b7de9',
        pending:   '#e0a800',
        fetched:   '#0dcaf0',
        failed:    '#dc3545',
        canceled:  '#6c757d',
    };

    const getStatusColor = (status) => STATUS_COLORS[status] || '#6c757d';
    const getProgressPercentage = (job) => {
        if (!job.step_count || job.step_count === 0) return 0;
        return Math.round((job.completed_steps / job.step_count) * 100);
    };
    const formatDate = (d) => new Date(d).toLocaleString();

    const authHeaders = () => ({
        'Content-Type': 'application/json',
        'Authorization': `Token ${localStorage.getItem('token')}`,
    });

    const cancelJob = async (e, jobId) => {
        e.stopPropagation();
        if (!window.confirm('Cancel this job?')) return;
        try {
            const res = await fetch('/job-queue/cancel-job/', {
                method: 'POST', headers: authHeaders(),
                body: JSON.stringify({ job_id: jobId }),
            });
            if (!res.ok) { const err = await res.json(); throw new Error(err.error || 'Failed'); }
            if (selectedJob?.job_id === jobId) setSelectedJob({ ...selectedJob, status: 'canceled' });
            fetchJobs(); fetchStatistics();
        } catch (err) { alert(err.message); }
    };

    const resumeJob = async (e, jobId) => {
        e.stopPropagation();
        if (!window.confirm('Resume this job?')) return;
        try {
            const res = await fetch('/job-queue/resume-job/', {
                method: 'POST', headers: authHeaders(),
                body: JSON.stringify({ job_id: jobId }),
            });
            if (!res.ok) { const err = await res.json(); throw new Error(err.error || 'Failed'); }
            if (selectedJob?.job_id === jobId) setSelectedJob({ ...selectedJob, status: 'pending' });
            fetchJobs(); fetchStatistics();
        } catch (err) { alert(err.message); }
    };

    const FILTER_TABS = [
        { label: 'All',       value: '' },
        { label: 'Pending',   value: 'pending' },
        { label: 'Running',   value: 'running' },
        { label: 'Completed', value: 'completed' },
        { label: 'Failed',    value: 'failed' },
        { label: 'Canceled',  value: 'canceled' },
    ];

    // ── Loading ────────────────────────────────────────────────────────────────
    if (isLoading) {
        return (
            <div className="mj-container">
                <div className="mj-header">
                    <button className="mj-btn-ghost" onClick={onBack}>← Back</button>
                    <h1 className="mj-title">Jobs</h1>
                </div>
                <div className="mj-empty">Loading…</div>
            </div>
        );
    }

    // ── Detail view ────────────────────────────────────────────────────────────
    if (selectedJob) {
        const isPending  = selectedJob.status === 'pending';
        const isCanceled = selectedJob.status === 'canceled';
        const pct = getProgressPercentage(selectedJob);

        return (
            <div className="mj-container">
                <div className="mj-header">
                    <button className="mj-btn-ghost" onClick={closeJobDetail}>← Back</button>
                    <h1 className="mj-title">Job Details</h1>
                    <button className="mj-btn-ghost" onClick={() => { fetchJobs(); fetchStatistics(); }}>Refresh</button>
                </div>

                <div className="mj-detail-card">
                    {/* Top row: ID + status */}
                    <div className="mj-detail-top">
                        <div>
                            <div className="mj-detail-id">{selectedJob.job_id}</div>
                            <div className="mj-detail-date">Created {formatDate(selectedJob.created_at)}</div>
                        </div>
                        <span className="mj-status-pill" style={{ background: getStatusColor(selectedJob.status) }}>
                            {selectedJob.status.toUpperCase()}
                        </span>
                    </div>

                    {/* Progress bar */}
                    <div className="mj-detail-progress">
                        <div className="mj-progress-meta">
                            <span>{selectedJob.completed_steps} / {selectedJob.step_count} steps</span>
                            <span>{pct}%</span>
                        </div>
                        <div className="mj-progress-track">
                            <div className="mj-progress-fill"
                                style={{ width: `${pct}%`, background: getStatusColor(selectedJob.status) }} />
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="mj-detail-actions">
                        <button
                            className="mj-action-cancel"
                            onClick={(e) => cancelJob(e, selectedJob.job_id)}
                            disabled={!isPending}
                        >
                            ✕ Cancel Job
                        </button>
                        <button
                            className="mj-action-resume"
                            onClick={(e) => resumeJob(e, selectedJob.job_id)}
                            disabled={!isCanceled}
                        >
                            ↺ Resume Job
                        </button>
                    </div>

                    {/* Pipeline steps */}
                    <div className="mj-steps-section">
                        <div className="mj-steps-label">PIPELINE STEPS</div>
                        <div className="mj-steps-track">
                            {selectedJob.job_steps.map((step, idx) => {
                                const color = getStatusColor(step.status);
                                const isLast = idx === selectedJob.job_steps.length - 1;
                                return (
                                    <div key={idx} className="mj-step-row">
                                        <div className="mj-step-left">
                                            <div className="mj-step-dot" style={{ borderColor: color, background: step.status === 'pending' ? 'transparent' : color }} />
                                            {!isLast && <div className="mj-step-line" />}
                                        </div>
                                        <div className="mj-step-body">
                                            <span className="mj-step-name">{step.function}</span>
                                            <span className="mj-step-status" style={{ color }}>{step.status}</span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    const formatRefreshed = (d) => d
        ? `Updated ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`
        : '';

    // ── List view ──────────────────────────────────────────────────────────────
    return (
        <div className="mj-container">
            <div className="mj-header">
                <button className="mj-btn-ghost" onClick={onBack}>← Back</button>
                <h1 className="mj-title">Jobs</h1>
                <span className="mj-live-badge">
                    <span className="mj-live-dot" />
                    Live
                </span>
                {lastRefreshed && (
                    <span className="mj-last-refreshed">{formatRefreshed(lastRefreshed)}</span>
                )}
                <button className="mj-btn-ghost" onClick={() => { fetchJobs(); fetchStatistics(); }}>Refresh</button>
            </div>

            {/* Stats */}
            {statistics && (
                <div className="mj-stats">
                    {[
                        { label: 'Total',     value: statistics.total_jobs,                    color: '#1e1e1e' },
                        { label: 'Pending',   value: statistics.status_breakdown.pending,      color: STATUS_COLORS.pending },
                        { label: 'Running',   value: statistics.status_breakdown.running,      color: STATUS_COLORS.running },
                        { label: 'Completed', value: statistics.status_breakdown.completed,    color: STATUS_COLORS.completed },
                        { label: 'Failed',    value: statistics.status_breakdown.failed,       color: STATUS_COLORS.failed },
                        { label: 'Canceled',  value: statistics.status_breakdown.canceled,     color: STATUS_COLORS.canceled },
                    ].map(s => (
                        <div className="mj-stat" key={s.label}>
                            <div className="mj-stat-value" style={{ color: s.color }}>{s.value}</div>
                            <div className="mj-stat-label">{s.label}</div>
                        </div>
                    ))}
                </div>
            )}

            {/* Filter tabs */}
            <div className="mj-filters">
                {FILTER_TABS.map(tab => (
                    <button
                        key={tab.value}
                        className={`mj-filter${statusFilter === tab.value ? ' active' : ''}`}
                        onClick={() => setStatusFilter(tab.value)}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {error && <div className="mj-error">{error}</div>}

            {jobs.length === 0 ? (
                <div className="mj-empty">No jobs found.</div>
            ) : (
                <div className="mj-table">
                    <div className="mj-table-head">
                        <span>Job ID</span>
                        <span>Status</span>
                        <span>Created</span>
                        <span>Progress</span>
                        <span></span>
                    </div>
                    {jobs.map(job => {
                        const isPending  = job.status === 'pending';
                        const isCanceled = job.status === 'canceled';
                        const pct = getProgressPercentage(job);
                        return (
                            <div key={job.job_id} className="mj-table-row" onClick={() => openJobDetail(job)}>
                                <span className="mj-job-id">{job.job_id.substring(0, 8)}…</span>
                                <span>
                                    <span className="mj-status-pill" style={{ background: getStatusColor(job.status) }}>
                                        {job.status.toUpperCase()}
                                    </span>
                                </span>
                                <span className="mj-date">{formatDate(job.created_at)}</span>
                                <span className="mj-progress-cell">
                                    <div className="mj-progress-track">
                                        <div className="mj-progress-fill"
                                            style={{ width: `${pct}%`, background: getStatusColor(job.status) }} />
                                    </div>
                                    <span className="mj-progress-pct">{job.completed_steps}/{job.step_count}</span>
                                </span>
                                <span className="mj-row-actions" onClick={e => e.stopPropagation()}>
                                    <button className="mj-row-btn cancel"
                                        disabled={!isPending}
                                        onClick={(e) => cancelJob(e, job.job_id)}
                                        title="Cancel">✕</button>
                                    <button className="mj-row-btn resume"
                                        disabled={!isCanceled}
                                        onClick={(e) => resumeJob(e, job.job_id)}
                                        title="Resume">↺</button>
                                    <button className="mj-row-btn details"
                                        onClick={() => openJobDetail(job)}>Details →</button>
                                </span>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

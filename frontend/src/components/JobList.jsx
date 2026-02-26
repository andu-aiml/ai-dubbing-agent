import React from 'react';

export default function JobList({ jobs, activeJobId, onSelectJob, onDeleteJob }) {
    if (jobs.length === 0) {
        return (
            <div className="sidebar__section">
                <div className="sidebar__section-title">Projects</div>
                <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>
                    No projects yet. Upload a video to begin.
                </div>
            </div>
        );
    }

    return (
        <div className="sidebar__section" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div className="sidebar__section-title">Projects ({jobs.length})</div>
            <div className="job-list">
                {jobs.map((job) => (
                    <div
                        key={job.job_id}
                        className={`job-card ${activeJobId === job.job_id ? 'job-card--active' : ''}`}
                        onClick={() => onSelectJob(job.job_id)}
                    >
                        <div className="job-card__header">
                            <span className="job-card__name" title={job.filename}>
                                {job.filename || `Job ${job.job_id}`}
                            </span>
                            <span className={`job-card__status job-card__status--${job.status}`}>
                                {job.status}
                            </span>
                        </div>
                        <div className="job-card__meta">
                            {job.file_size_mb} MB • ID: {job.job_id}
                        </div>
                        {job.status === 'processing' && (
                            <div className="job-card__progress">
                                <div
                                    className="job-card__progress-bar"
                                    style={{ width: `${job.progress || 0}%` }}
                                />
                            </div>
                        )}
                        {(job.status === 'completed' || job.status === 'failed') && (
                            <div style={{ marginTop: '8px', display: 'flex', gap: '6px' }}>
                                {job.status === 'completed' && (
                                    <a
                                        href={`http://localhost:8000/api/download/${job.job_id}`}
                                        className="btn btn--primary btn--sm"
                                        onClick={(e) => e.stopPropagation()}
                                        download
                                    >
                                        ⬇ Download
                                    </a>
                                )}
                                <button
                                    className="btn btn--danger btn--sm"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onDeleteJob(job.job_id);
                                    }}
                                >
                                    ✕ Delete
                                </button>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}

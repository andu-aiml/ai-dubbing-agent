import React from 'react';

export default function ControlPanel({ activeJob, settings, onSettingsChange }) {
    const segments = activeJob?.segments || [];

    return (
        <div className="controls-panel">
            {/* Settings */}
            <div className="controls-panel__section">
                <div className="controls-panel__section-title">Pipeline Settings</div>

                <div className="control-group">
                    <label className="control-group__label">Source Language</label>
                    <select
                        className="control-group__select"
                        value={settings.sourceLang}
                        onChange={(e) => onSettingsChange({ ...settings, sourceLang: e.target.value })}
                    >
                        <option value="hi">Hindi (हिन्दी)</option>
                        <option value="ta">Tamil (தமிழ்)</option>
                        <option value="te">Telugu (తెలుగు)</option>
                        <option value="bn">Bengali (বাংলা)</option>
                        <option value="mr">Marathi (मराठी)</option>
                    </select>
                </div>

                <div className="control-group">
                    <label className="control-group__label">Target Language</label>
                    <select className="control-group__select" value="en" disabled>
                        <option value="en">English</option>
                    </select>
                </div>

                <div className="control-group">
                    <label className="control-group__label">Whisper Model</label>
                    <select
                        className="control-group__select"
                        value={settings.whisperModel}
                        onChange={(e) => onSettingsChange({ ...settings, whisperModel: e.target.value })}
                    >
                        <option value="tiny">Tiny (fastest)</option>
                        <option value="base">Base</option>
                        <option value="small">Small</option>
                        <option value="medium">Medium (recommended)</option>
                        <option value="large">Large (best quality)</option>
                    </select>
                </div>

                <div className="toggle">
                    <span className="toggle__label">HD Lip Sync (GAN)</span>
                    <div
                        className={`toggle__switch ${settings.useHd ? 'toggle__switch--on' : ''}`}
                        onClick={() => onSettingsChange({ ...settings, useHd: !settings.useHd })}
                    >
                        <div className="toggle__switch-thumb" />
                    </div>
                </div>

                <div className="toggle">
                    <span className="toggle__label">Auto-process on upload</span>
                    <div
                        className={`toggle__switch ${settings.autoProcess ? 'toggle__switch--on' : ''}`}
                        onClick={() => onSettingsChange({ ...settings, autoProcess: !settings.autoProcess })}
                    >
                        <div className="toggle__switch-thumb" />
                    </div>
                </div>
            </div>

            {/* Job Info */}
            {activeJob && (
                <div className="controls-panel__section">
                    <div className="controls-panel__section-title">Job Details</div>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <div><span style={{ color: 'var(--text-muted)' }}>ID:</span> <span className="text-mono">{activeJob.job_id}</span></div>
                        <div><span style={{ color: 'var(--text-muted)' }}>Status:</span> <span style={{ color: activeJob.status === 'completed' ? 'var(--accent-success)' : 'var(--accent-primary)', textTransform: 'capitalize' }}>{activeJob.status}</span></div>
                        <div><span style={{ color: 'var(--text-muted)' }}>Step:</span> {activeJob.current_step || '—'}</div>
                        <div><span style={{ color: 'var(--text-muted)' }}>Size:</span> {activeJob.file_size_mb} MB</div>
                        {activeJob.error && (
                            <div style={{ color: 'var(--accent-danger)', marginTop: '4px', padding: '8px', background: 'rgba(231,76,60,0.08)', borderRadius: '6px', fontSize: 'var(--text-xs)' }}>
                                ⚠ {activeJob.error}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Transcript */}
            {segments.length > 0 && (
                <div className="controls-panel__section" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                    <div className="controls-panel__section-title">Transcript ({segments.length} segments)</div>
                    <div className="segment-list">
                        {segments.map((seg, i) => (
                            <div key={i} className="segment-item">
                                <span className="segment-item__time">
                                    {formatTime(seg.start)}
                                </span>
                                <span className="segment-item__text">{seg.text}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

import React, { useState } from 'react';

export default function VideoPreview({ activeJob, getPreviewUrl, getDownloadUrl }) {
    const [viewMode, setViewMode] = useState('single'); // 'single' | 'dual'
    const [showOriginal, setShowOriginal] = useState(true);

    if (!activeJob) {
        return (
            <div className="preview-panel">
                <div className="preview-panel__toolbar">
                    <button className="preview-panel__toolbar-btn preview-panel__toolbar-btn--active">Source</button>
                    <button className="preview-panel__toolbar-btn">Dubbed</button>
                    <button className="preview-panel__toolbar-btn">Compare</button>
                </div>
                <div className="preview-panel__viewport">
                    <div className="preview-panel__empty">
                        <div className="preview-panel__empty-icon">🎥</div>
                        <div className="preview-panel__empty-text">
                            Upload a Hindi video to start the dubbing pipeline
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    const hasOutput = activeJob.status === 'completed';

    return (
        <div className="preview-panel">
            <div className="preview-panel__toolbar">
                <button
                    className={`preview-panel__toolbar-btn ${viewMode === 'single' && showOriginal ? 'preview-panel__toolbar-btn--active' : ''}`}
                    onClick={() => { setViewMode('single'); setShowOriginal(true); }}
                >
                    Source
                </button>
                {hasOutput && (
                    <>
                        <button
                            className={`preview-panel__toolbar-btn ${viewMode === 'single' && !showOriginal ? 'preview-panel__toolbar-btn--active' : ''}`}
                            onClick={() => { setViewMode('single'); setShowOriginal(false); }}
                        >
                            Dubbed
                        </button>
                        <button
                            className={`preview-panel__toolbar-btn ${viewMode === 'dual' ? 'preview-panel__toolbar-btn--active' : ''}`}
                            onClick={() => setViewMode('dual')}
                        >
                            Compare
                        </button>
                    </>
                )}
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginLeft: 'auto' }}>
                    {activeJob.filename}
                </span>
            </div>

            <div className="preview-panel__viewport">
                {viewMode === 'dual' && hasOutput ? (
                    <div className="dual-preview">
                        <div className="dual-preview__pane">
                            <span className="dual-preview__label">Original</span>
                            <div className="dual-preview__video-wrap">
                                <video
                                    src={getPreviewUrl(activeJob.job_id)}
                                    controls
                                    className="preview-panel__video"
                                />
                            </div>
                        </div>
                        <div className="dual-preview__pane">
                            <span className="dual-preview__label">Dubbed</span>
                            <div className="dual-preview__video-wrap">
                                <video
                                    src={getDownloadUrl(activeJob.job_id)}
                                    controls
                                    className="preview-panel__video"
                                />
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="preview-panel__video-container">
                        <video
                            key={showOriginal ? 'input' : 'output'}
                            src={
                                showOriginal
                                    ? getPreviewUrl(activeJob.job_id)
                                    : hasOutput
                                        ? getDownloadUrl(activeJob.job_id)
                                        : getPreviewUrl(activeJob.job_id)
                            }
                            controls
                            className="preview-panel__video"
                        />
                    </div>
                )}
            </div>
        </div>
    );
}

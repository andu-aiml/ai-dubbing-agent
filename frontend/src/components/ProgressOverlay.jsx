import React from 'react';

const STEPS = [
    { key: 'asr', label: 'Speech Recognition', detail: 'Transcribing Hindi & translating to English', icon: '🎤' },
    { key: 'tts', label: 'Voice Synthesis', detail: 'Cloning voice & generating English speech', icon: '🔊' },
    { key: 'wav2lip', label: 'Lip Synchronization', detail: 'Syncing lip movements to dubbed audio', icon: '👄' },
];

const STEP_ORDER = ['asr', 'tts', 'wav2lip', 'done'];

export default function ProgressOverlay({ job, progress }) {
    if (!job || job.status !== 'processing') return null;

    const currentStepIndex = STEP_ORDER.indexOf(job.current_step);
    const progressPercent = progress?.progress || (currentStepIndex >= 0 ? (currentStepIndex / 3) * 100 : 0);

    return (
        <div className="progress-overlay">
            <div className="progress-card">
                <div className="progress-card__title">Processing Pipeline</div>

                <div className="progress-card__steps">
                    {STEPS.map((step, i) => {
                        const stepIndex = STEP_ORDER.indexOf(step.key);
                        const isActive = job.current_step === step.key;
                        const isDone = currentStepIndex > stepIndex;

                        return (
                            <div key={step.key} className="progress-step">
                                <div
                                    className={`progress-step__icon ${isActive ? 'progress-step__icon--active' : ''} ${isDone ? 'progress-step__icon--done' : ''}`}
                                >
                                    {isDone ? '✓' : isActive ? <span className="spin">⟳</span> : step.icon}
                                </div>
                                <div className="progress-step__info">
                                    <div className="progress-step__label">{step.label}</div>
                                    <div className="progress-step__detail">
                                        {isDone ? 'Complete' : isActive ? step.detail : 'Waiting...'}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>

                <div className="progress-card__bar">
                    <div
                        className="progress-card__bar-fill"
                        style={{ width: `${progressPercent}%` }}
                    />
                </div>

                <div className="progress-card__message">
                    {progress?.message || 'Initializing pipeline...'}
                </div>
            </div>
        </div>
    );
}

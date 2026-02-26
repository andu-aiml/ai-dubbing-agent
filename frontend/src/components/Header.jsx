import React from 'react';

export default function Header({ health }) {
    const services = health?.services || {};

    return (
        <header className="header">
            <div className="header__brand">
                <div className="header__logo">D</div>
                <h1 className="header__title">DubStudio</h1>
                <span className="header__subtitle">Professional Video Dubbing</span>
            </div>
            <div className="header__services">
                {['asr', 'tts', 'wav2lip'].map((name) => {
                    const svc = services[name];
                    const ok = svc?.status === 'ok';
                    const labels = { asr: 'ASR', tts: 'TTS', wav2lip: 'Lip Sync' };
                    return (
                        <div className="service-dot" key={name} title={ok ? 'Connected' : 'Unreachable'}>
                            <span className={`service-dot__indicator ${ok ? 'service-dot__indicator--ok' : 'service-dot__indicator--error'}`} />
                            <span>{labels[name]}</span>
                        </div>
                    );
                })}
            </div>
        </header>
    );
}

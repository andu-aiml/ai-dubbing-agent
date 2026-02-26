import React, { useMemo } from 'react';

export default function Timeline({ activeJob }) {
    const segments = activeJob?.segments || [];

    // Calculate total duration from segments
    const totalDuration = useMemo(() => {
        if (segments.length === 0) return 60;
        return Math.max(...segments.map(s => s.end), 30);
    }, [segments]);

    // Generate pseudo-waveform bars
    const waveformBars = useMemo(() => {
        return Array.from({ length: 120 }, () => Math.random() * 0.8 + 0.2);
    }, []);

    return (
        <div className="timeline">
            <div className="timeline__header">
                <span className="timeline__title">Timeline</span>
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {formatDuration(totalDuration)}
                </span>
            </div>
            <div className="timeline__tracks">
                {/* Video Track */}
                <div className="timeline__track">
                    <span className="timeline__track-label">🎬 Video</span>
                    <div className="timeline__track-content">
                        {segments.length > 0 ? (
                            segments.map((seg, i) => (
                                <div
                                    key={i}
                                    className="timeline__segment timeline__segment--video"
                                    style={{
                                        left: `${(seg.start / totalDuration) * 100}%`,
                                        width: `${((seg.end - seg.start) / totalDuration) * 100}%`,
                                    }}
                                    title={`${formatTime(seg.start)} — ${seg.text.substring(0, 40)}...`}
                                />
                            ))
                        ) : (
                            <div
                                className="timeline__segment timeline__segment--video"
                                style={{ left: 0, width: '100%' }}
                            />
                        )}
                    </div>
                </div>

                {/* Audio Waveform Track */}
                <div className="timeline__track">
                    <span className="timeline__track-label">🔊 Audio</span>
                    <div className="timeline__waveform">
                        {waveformBars.map((h, i) => (
                            <div
                                key={i}
                                className="timeline__waveform-bar"
                                style={{ height: `${h * 100}%` }}
                            />
                        ))}
                    </div>
                </div>

                {/* Dubbed Audio Track */}
                {activeJob?.status === 'completed' && (
                    <div className="timeline__track">
                        <span className="timeline__track-label">🎙 Dubbed</span>
                        <div className="timeline__track-content">
                            {segments.map((seg, i) => (
                                <div
                                    key={i}
                                    className="timeline__segment timeline__segment--audio"
                                    style={{
                                        left: `${(seg.start / totalDuration) * 100}%`,
                                        width: `${((seg.end - seg.start) / totalDuration) * 100}%`,
                                    }}
                                />
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatDuration(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.00`;
}

import React, { useRef, useState, useCallback } from 'react';

export default function UploadPanel({ onUpload, loading }) {
    const inputRef = useRef(null);
    const [dragging, setDragging] = useState(false);

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        setDragging(false);
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('video/')) {
            onUpload(file);
        }
    }, [onUpload]);

    const handleDragOver = useCallback((e) => {
        e.preventDefault();
        setDragging(true);
    }, []);

    const handleDragLeave = useCallback(() => setDragging(false), []);

    const handleClick = () => inputRef.current?.click();

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file) onUpload(file);
    };

    return (
        <div className="sidebar__section">
            <div className="sidebar__section-title">Import</div>
            <div
                className={`upload-zone ${dragging ? 'upload-zone--active' : ''}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={handleClick}
            >
                <div className="upload-zone__icon">
                    {loading ? (
                        <span className="spin">⟳</span>
                    ) : (
                        '🎬'
                    )}
                </div>
                <div className="upload-zone__text">
                    {loading ? (
                        'Uploading...'
                    ) : (
                        <>
                            <strong>Drop video here</strong> or click to browse
                        </>
                    )}
                </div>
                <div className="upload-zone__formats">MP4, AVI, MOV • Hindi audio</div>
                <input
                    ref={inputRef}
                    type="file"
                    accept="video/*"
                    style={{ display: 'none' }}
                    onChange={handleFileChange}
                />
            </div>
        </div>
    );
}

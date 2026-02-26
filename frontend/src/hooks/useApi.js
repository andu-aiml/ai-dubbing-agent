import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function useApi() {
    const [jobs, setJobs] = useState([]);
    const [health, setHealth] = useState(null);
    const [loading, setLoading] = useState(false);
    const wsRefs = useRef({});

    // Fetch all jobs
    const fetchJobs = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/jobs`);
            const data = await res.json();
            setJobs(data.jobs || []);
        } catch (err) {
            console.error('Failed to fetch jobs:', err);
        }
    }, []);

    // Fetch health status
    const fetchHealth = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/health`);
            const data = await res.json();
            setHealth(data);
        } catch {
            setHealth({ status: 'offline', services: {} });
        }
    }, []);

    // Upload video
    const uploadVideo = useCallback(async (file, useHd = false) => {
        setLoading(true);
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('use_hd', useHd);

            const res = await fetch(`${API_BASE}/api/upload`, {
                method: 'POST',
                body: formData,
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Upload failed');

            // Refresh jobs list
            await fetchJobs();
            return data;
        } catch (err) {
            console.error('Upload failed:', err);
            throw err;
        } finally {
            setLoading(false);
        }
    }, [fetchJobs]);

    // Connect WebSocket for job progress
    const connectWebSocket = useCallback((jobId, onProgress) => {
        const wsUrl = API_BASE.replace(/^http/, 'ws');
        const ws = new WebSocket(`${wsUrl}/ws/progress/${jobId}`);

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            onProgress(data);
            // Update job in list
            setJobs(prev => prev.map(j => j.job_id === jobId ? { ...j, ...data } : j));
        };

        ws.onerror = (err) => console.error('WebSocket error:', err);
        wsRefs.current[jobId] = ws;

        return () => {
            ws.close();
            delete wsRefs.current[jobId];
        };
    }, []);

    // Delete job
    const deleteJob = useCallback(async (jobId) => {
        try {
            await fetch(`${API_BASE}/api/jobs/${jobId}`, { method: 'DELETE' });
            setJobs(prev => prev.filter(j => j.job_id !== jobId));
        } catch (err) {
            console.error('Delete failed:', err);
        }
    }, []);

    // Get preview/download URLs
    const getPreviewUrl = useCallback((jobId) => `${API_BASE}/api/preview/${jobId}`, []);
    const getDownloadUrl = useCallback((jobId) => `${API_BASE}/api/download/${jobId}`, []);

    // Poll jobs periodically
    useEffect(() => {
        fetchJobs();
        fetchHealth();
        const interval = setInterval(() => {
            fetchJobs();
            fetchHealth();
        }, 5000);
        return () => clearInterval(interval);
    }, [fetchJobs, fetchHealth]);

    // Cleanup WebSockets
    useEffect(() => {
        return () => {
            Object.values(wsRefs.current).forEach(ws => ws.close());
        };
    }, []);

    return {
        jobs,
        health,
        loading,
        uploadVideo,
        deleteJob,
        fetchJobs,
        fetchHealth,
        connectWebSocket,
        getPreviewUrl,
        getDownloadUrl,
    };
}

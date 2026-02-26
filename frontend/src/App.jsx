import React, { useState, useCallback, useEffect } from 'react';
import { useApi } from './hooks/useApi';
import Header from './components/Header';
import UploadPanel from './components/UploadPanel';
import JobList from './components/JobList';
import VideoPreview from './components/VideoPreview';
import ControlPanel from './components/ControlPanel';
import Timeline from './components/Timeline';
import ProgressOverlay from './components/ProgressOverlay';
import './App.css';

export default function App() {
  const {
    jobs,
    health,
    loading,
    uploadVideo,
    deleteJob,
    connectWebSocket,
    getPreviewUrl,
    getDownloadUrl,
  } = useApi();

  const [activeJobId, setActiveJobId] = useState(null);
  const [progress, setProgress] = useState(null);
  const [settings, setSettings] = useState({
    sourceLang: 'hi',
    whisperModel: 'medium',
    useHd: false,
    autoProcess: true,
  });

  // Auto-select the first job or latest
  useEffect(() => {
    if (jobs.length > 0 && !activeJobId) {
      setActiveJobId(jobs[0].job_id);
    }
  }, [jobs, activeJobId]);

  const activeJob = jobs.find((j) => j.job_id === activeJobId) || null;

  // Connect WebSocket when a processing job is active
  useEffect(() => {
    if (activeJob?.status === 'processing') {
      const cleanup = connectWebSocket(activeJob.job_id, (data) => {
        setProgress(data);
      });
      return cleanup;
    } else {
      setProgress(null);
    }
  }, [activeJob?.job_id, activeJob?.status, connectWebSocket]);

  const handleUpload = useCallback(
    async (file) => {
      try {
        const result = await uploadVideo(file, settings.useHd);
        setActiveJobId(result.job_id);
      } catch (err) {
        console.error('Upload error:', err);
      }
    },
    [uploadVideo, settings.useHd]
  );

  const handleSelectJob = useCallback((jobId) => {
    setActiveJobId(jobId);
  }, []);

  const handleDeleteJob = useCallback(
    async (jobId) => {
      await deleteJob(jobId);
      if (activeJobId === jobId) {
        setActiveJobId(null);
      }
    },
    [deleteJob, activeJobId]
  );

  // Find the processing job for overlay (could be different from active)
  const processingJob = jobs.find((j) => j.status === 'processing');

  return (
    <>
      <div className="app-layout">
        <Header health={health} />

        <div className="sidebar">
          <UploadPanel onUpload={handleUpload} loading={loading} />
          <JobList
            jobs={jobs}
            activeJobId={activeJobId}
            onSelectJob={handleSelectJob}
            onDeleteJob={handleDeleteJob}
          />
        </div>

        <VideoPreview
          activeJob={activeJob}
          getPreviewUrl={getPreviewUrl}
          getDownloadUrl={getDownloadUrl}
        />

        <ControlPanel
          activeJob={activeJob}
          settings={settings}
          onSettingsChange={setSettings}
        />

        <Timeline activeJob={activeJob} />
      </div>

      <ProgressOverlay job={processingJob} progress={progress} />
    </>
  );
}

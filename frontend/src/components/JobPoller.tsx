"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import styles from "./components.module.css";
import LogViewer from "./LogViewer";

type Job = {
  id: string;
  job_type: string;
  status: string;
  created_at: string;
  error_message?: string;
  result_json?: any;
  logs?: string;
};

export default function JobPoller() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  const fetchJobs = useCallback(async () => {
    try {
      const data = await api.get("/jobs");
      setJobs(data);
      
      // Update selected job if it's currently open, using functional state update
      setSelectedJob(prev => {
        if (!prev) return prev;
        const updated = data.find((j: Job) => j.id === prev.id);
        return updated || prev;
      });
    } catch (err) {
      console.error("Failed to fetch jobs", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(() => {
      fetchJobs();
    }, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, [fetchJobs]);

  const handleDownload = async (jobId: string) => {
    try {
      window.open(`/api/jobs/${jobId}/download`, '_blank');
    } catch (err) {
      console.error("Download failed", err);
      alert("Failed to download file");
    }
  };

  const handleTerminate = async (jobId: string) => {
    try {
      await api.post(`/jobs/${jobId}/terminate`, {});
      fetchJobs();
    } catch (err) {
      console.error("Failed to terminate job", err);
      alert("Failed to terminate job");
    }
  };

  const handleDelete = async (jobId: string) => {
    if (!confirm("Are you sure you want to permanently delete this job and its files?")) return;
    try {
      await api.delete(`/jobs/${jobId}`);
      fetchJobs();
    } catch (err: any) {
      console.error("Failed to delete job", err);
      alert(err.response?.data?.detail || "Failed to delete job");
    }
  };

  if (loading) return <div className={styles.emptyState}>Loading jobs...</div>;

  if (jobs.length === 0) {
    return <div className={styles.emptyState}>No jobs found. Submit one to get started!</div>;
  }

  return (
    <div className={styles.jobList}>
      {jobs.map((job) => (
        <div key={job.id} className={styles.jobCard}>
          <div className={styles.jobHeader}>
            <span className={styles.jobType}>{job.job_type.replace("-", " ")}</span>
            <span className={`${styles.jobStatus} ${styles[`status-${job.status}`]}`}>
              {job.error_message === "Terminated by user." ? "TERMINATED" : job.status}
            </span>
          </div>
          <div className={styles.jobTime}>
            {new Date(job.created_at).toLocaleString()}
          </div>

          {job.status === "failed" && job.error_message && job.error_message !== "Terminated by user." && (
            <div className={styles.error} style={{ marginTop: 0, marginBottom: "1rem" }}>
              Error: {job.error_message}
            </div>
          )}

          <div className={styles.jobActions}>
            <button 
              className={styles.actionBtn}
              onClick={() => setSelectedJob(job)}
            >
              Details
            </button>
            {job.status === "completed" && (job.job_type === "humanize" || job.job_type === "fix-plagiarism") && (
              <button 
                className={`${styles.actionBtn} ${styles.actionBtnPrimary}`}
                onClick={() => handleDownload(job.id)}
              >
                Download Result
              </button>
            )}
            
            {(job.status === "pending" || job.status === "processing") ? (
              <button 
                className={`${styles.actionBtn} ${styles.actionBtnDanger}`}
                onClick={() => handleTerminate(job.id)}
              >
                Cancel
              </button>
            ) : (
              <button 
                className={`${styles.actionBtn} ${styles.actionBtnDanger}`}
                onClick={() => handleDelete(job.id)}
              >
                Delete
              </button>
            )}
          </div>
        </div>
      ))}

      {selectedJob && (
        <LogViewer 
          logs={selectedJob.logs || ""} 
          status={selectedJob.status} 
          onClose={() => setSelectedJob(null)} 
        />
      )}
    </div>
  );
}

"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import styles from "./components.module.css";

export default function ToolForm() {
  const [jobType, setJobType] = useState("humanize");
  const [file, setFile] = useState<File | null>(null);
  const [githubUrl, setGithubUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setMessage({ text: "Please select a file", isError: true });
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const formData = new FormData();
      formData.append("job_type", jobType);
      formData.append("file", file);
      if (githubUrl) {
        formData.append("github_url", githubUrl);
      }
      
      await api.postForm(`/paper/${jobType}`, formData);
      
      setMessage({ text: "Job submitted successfully!", isError: false });
      setFile(null);
      setGithubUrl("");
      // Reset file input via form reset or uncontrolled ref, here we just let it be
    } catch (err: any) {
      setMessage({ text: err.message || "Failed to submit job", isError: true });
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className={styles.formGroup}>
        <label className={styles.label}>Job Type</label>
        <select 
          className={styles.select} 
          value={jobType} 
          onChange={(e) => setJobType(e.target.value)}
        >
          <option value="humanize">Humanize Text</option>
          <option value="check-plagiarism">Check Plagiarism</option>
          <option value="fix-plagiarism">Fix Plagiarism</option>
          <option value="check-ai-phrases">Check AI Phrases</option>
        </select>
      </div>

      <div className={styles.formGroup}>
        <label className={styles.label}>Document (.txt, .docx)</label>
        <input 
          type="file" 
          className={styles.input} 
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          accept=".txt,.docx"
          required
        />
      </div>

      {(jobType === "humanize" || jobType === "fix-plagiarism") && (
        <div className={styles.formGroup}>
          <label className={styles.label}>GitHub Context URL (Optional)</label>
          <input 
            type="url" 
            className={styles.input} 
            placeholder="https://github.com/user/repo"
            value={githubUrl}
            onChange={(e) => setGithubUrl(e.target.value)}
          />
        </div>
      )}

      <button type="submit" className={styles.button} disabled={loading || !file}>
        {loading ? "Submitting..." : "Submit Job"}
      </button>

      {message && (
        <div className={message.isError ? styles.error : styles.success}>
          {message.text}
        </div>
      )}
    </form>
  );
}

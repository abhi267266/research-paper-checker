"use client";

import { useEffect, useRef } from "react";
import styles from "./components.module.css";

interface LogViewerProps {
  logs: string;
  onClose: () => void;
  status: string;
}

export default function LogViewer({ logs, onClose, status }: LogViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className={styles.logOverlay}>
      <div className={styles.logContainer}>
        <div className={styles.logHeader}>
          <div className={styles.logTitle}>
            <span className={styles.terminalIcon}></span>
            Process Details - Status: <span className={`${styles.statusText} ${styles[`status-${status}`]}`}>{status.toUpperCase()}</span>
          </div>
          <button className={styles.closeBtn} onClick={onClose}>&times;</button>
        </div>
        <div className={styles.logContent} ref={scrollRef}>
          {logs ? (
            <pre className={styles.pre}>{logs}</pre>
          ) : (
            <div className={styles.noLogs}>Waiting for logs...</div>
          )}
        </div>
      </div>
    </div>
  );
}

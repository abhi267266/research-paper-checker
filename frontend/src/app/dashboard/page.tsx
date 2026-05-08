"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import styles from "./page.module.css";
import ToolForm from "@/components/ToolForm";
import JobPoller from "@/components/JobPoller";

export default function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<{ id: string; email: string } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check auth status
    api.get("/auth/me")
      .then((data) => {
        setUser(data);
        setLoading(false);
      })
      .catch(async () => {
        // Clear cookies if auth check fails to avoid redirect loop
        try {
          await api.post("/auth/logout", {});
        } catch (e) {
          // Ignore logout errors
        }
        router.push("/login");
      });
  }, [router]);

  const handleLogout = async () => {
    try {
      await api.post("/auth/logout", {});
      router.push("/login");
    } catch (err) {
      console.error("Logout failed", err);
    }
  };

  if (loading || !user) {
    return <div className={styles.wrapper}>Loading...</div>;
  }

  return (
    <div className={styles.wrapper}>
      <header className={styles.header}>
        <h1 className={styles.title}>Research Paper Platform</h1>
        <div className={styles.userInfo}>
          <span>{user.email}</span>
          <button className={styles.logoutButton} onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <div className={styles.grid}>
        <div className={styles.panel}>
          <h2 className={styles.panelTitle}>Submit Job</h2>
          <ToolForm />
        </div>

        <div className={styles.panel}>
          <h2 className={styles.panelTitle}>Your Jobs</h2>
          <JobPoller />
        </div>
      </div>
    </div>
  );
}

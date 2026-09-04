import React, { useEffect, useState } from "react";
import { api } from "../api/client";

interface BackupFile { filename: string; size_bytes: number; created_at: string; }

function formatSize(bytes: number) {
  const mb = bytes / (1024 * 1024);
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${(bytes / 1024).toFixed(0)} KB`;
}

export default function Backups() {
  const [backups, setBackups] = useState<BackupFile[]>([]);
  const [running, setRunning] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  function load() {
    api.get<{ backups: BackupFile[] }>("/api/backups").then((res) => setBackups(res.backups));
  }
  useEffect(load, []);

  async function runNow() {
    setRunning(true);
    setMsg(null);
    try {
      await api.post("/api/backups/run-now");
      setMsg("⏳ Backup در پس‌زمینه شروع شد. چند دقیقه بعد این صفحه را رفرش کنید.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      <div className="topbar">
        <h2>پشتیبان‌گیری از دیتابیس</h2>
        <button onClick={runNow} disabled={running}>{running ? "در حال شروع..." : "اجرای دستی Backup"}</button>
      </div>
      {msg && <div className="card" style={{ marginBottom: 16, fontSize: 13 }}>{msg}</div>}
      <div className="card">
        <table>
          <thead><tr><th>نام فایل</th><th>حجم</th><th>تاریخ ایجاد</th></tr></thead>
          <tbody>
            {backups.map((b) => (
              <tr key={b.filename}>
                <td>{b.filename}</td>
                <td>{formatSize(b.size_bytes)}</td>
                <td>{new Date(b.created_at).toLocaleString("fa-IR")}</td>
              </tr>
            ))}
            {backups.length === 0 && <tr><td colSpan={3} style={{ textAlign: "center", color: "#888" }}>هنوز Backup ای ثبت نشده است</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

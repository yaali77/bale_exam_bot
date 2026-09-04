import React, { useEffect, useState } from "react";
import { api } from "../api/client";

interface LogEntry {
  id: string; action: string; actor_type: string; actor_id: string | null;
  target_type: string | null; target_id: string | null;
  previous_value: string | null; new_value: string | null; created_at: string;
}

export default function AuditLog() {
  const [logs, setLogs] = useState<LogEntry[]>([]);

  useEffect(() => { api.get<LogEntry[]>("/api/audit-logs").then(setLogs); }, []);

  return (
    <div>
      <div className="topbar"><h2>گزارش تغییرات (Audit Log)</h2></div>
      <div className="card">
        <table>
          <thead><tr><th>عملیات</th><th>عامل</th><th>هدف</th><th>مقدار قبلی</th><th>مقدار جدید</th><th>زمان</th></tr></thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id}>
                <td>{l.action}</td>
                <td>{l.actor_type}{l.actor_id ? ` (${l.actor_id.slice(0, 8)})` : ""}</td>
                <td>{l.target_type || "-"}{l.target_id ? ` / ${l.target_id.slice(0, 8)}` : ""}</td>
                <td>{l.previous_value || "-"}</td>
                <td>{l.new_value || "-"}</td>
                <td>{new Date(l.created_at).toLocaleString("fa-IR")}</td>
              </tr>
            ))}
            {logs.length === 0 && <tr><td colSpan={6} style={{ textAlign: "center", color: "#888" }}>رکوردی یافت نشد</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

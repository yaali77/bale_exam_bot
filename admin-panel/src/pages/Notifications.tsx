import React, { useEffect, useState } from "react";
import { api } from "../api/client";

interface BroadcastJob {
  id: string; message: string; audience: string; status: string;
  scheduled_at: string | null; sent_count: number; failed_count: number; created_at: string;
}

const STATUS_LABELS: Record<string, string> = {
  scheduled: "زمان‌بندی‌شده", sent: "ارسال‌شده", cancelled: "لغوشده", failed: "ناموفق",
};

export default function Notifications() {
  const [message, setMessage] = useState("");
  const [audience, setAudience] = useState("all");
  const [examId, setExamId] = useState("");
  const [scheduleAt, setScheduleAt] = useState("");
  const [sending, setSending] = useState(false);
  const [jobs, setJobs] = useState<BroadcastJob[]>([]);

  function loadJobs() {
    api.get<BroadcastJob[]>("/api/notifications/jobs").then(setJobs);
  }
  useEffect(loadJobs, []);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    setSending(true);
    try {
      await api.post("/api/notifications/broadcast", {
        message,
        audience,
        exam_id: examId || undefined,
        schedule_at: scheduleAt ? new Date(scheduleAt).toISOString() : undefined,
      });
      setMessage(""); setScheduleAt("");
      loadJobs();
    } finally {
      setSending(false);
    }
  }

  async function cancelJob(id: string) {
    await api.post(`/api/notifications/jobs/${id}/cancel`);
    loadJobs();
  }

  return (
    <div>
      <div className="topbar"><h2>اطلاع‌رسانی گروهی</h2></div>
      <form className="card" onSubmit={send} style={{ display: "grid", gap: 14, maxWidth: 520, marginBottom: 20 }}>
        <div className="field">
          <label>مخاطبان</label>
          <select value={audience} onChange={(e) => setAudience(e.target.value)}>
            <option value="all">همه کاربران</option>
            <option value="exam">شرکت‌کنندگان یک آزمون</option>
            <option value="passed">قبول‌شدگان یک آزمون</option>
            <option value="failed">مردودشدگان یک آزمون</option>
          </select>
        </div>
        {audience !== "all" && (
          <div className="field">
            <label>شناسه آزمون (Exam ID)</label>
            <input value={examId} onChange={(e) => setExamId(e.target.value)} placeholder="از صفحه آزمون‌ها کپی کنید" required />
          </div>
        )}
        <div className="field">
          <label>متن پیام</label>
          <textarea required rows={5} value={message} onChange={(e) => setMessage(e.target.value)} />
        </div>
        <div className="field">
          <label>زمان‌بندی ارسال (خالی = ارسال فوری)</label>
          <input type="datetime-local" value={scheduleAt} onChange={(e) => setScheduleAt(e.target.value)} />
        </div>
        <button type="submit" disabled={sending}>{sending ? "در حال ثبت..." : scheduleAt ? "زمان‌بندی پیام" : "ارسال فوری"}</button>
      </form>

      <div className="card">
        <h3 style={{ marginTop: 0, fontSize: 15 }}>تاریخچه و پیام‌های زمان‌بندی‌شده</h3>
        <table>
          <thead><tr><th>پیام</th><th>مخاطب</th><th>وضعیت</th><th>زمان اجرا</th><th>ارسال موفق/ناموفق</th><th>عملیات</th></tr></thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.id}>
                <td style={{ maxWidth: 220 }}>{j.message}</td>
                <td>{j.audience}</td>
                <td><span className={`badge ${j.status === "sent" ? "badge-green" : j.status === "failed" ? "badge-red" : "badge-gray"}`}>{STATUS_LABELS[j.status]}</span></td>
                <td>{j.scheduled_at ? new Date(j.scheduled_at).toLocaleString("fa-IR") : "فوری"}</td>
                <td>{j.sent_count} / {j.failed_count}</td>
                <td>
                  {j.status === "scheduled" && <button className="danger" onClick={() => cancelJob(j.id)}>لغو</button>}
                </td>
              </tr>
            ))}
            {jobs.length === 0 && <tr><td colSpan={6} style={{ textAlign: "center", color: "#888" }}>پیامی ثبت نشده است</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

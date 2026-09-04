import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

interface Exam {
  id: string;
  title: string;
  exam_code: string;
  exam_date: string;
  total_score: string;
  passing_score: string;
  status: string;
  is_active: boolean;
}

const STATUS_LABELS: Record<string, string> = {
  draft: "پیش‌نویس",
  entering: "در حال ثبت نمرات",
  review: "آماده بررسی",
  published: "منتشر شده",
  closed: "بسته شده",
};

export default function Exams() {
  const { hasPermission } = useAuth();
  const [exams, setExams] = useState<Exam[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", exam_code: "", exam_date: "", total_score: "100", passing_score: "60", description: "" });
  const [error, setError] = useState<string | null>(null);

  function load() {
    api.get<Exam[]>("/api/exams").then(setExams);
  }
  useEffect(load, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/api/exams", form);
      setShowForm(false);
      setForm({ title: "", exam_code: "", exam_date: "", total_score: "100", passing_score: "60", description: "" });
      load();
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function updateStatus(exam: Exam, status: string) {
    await api.patch(`/api/exams/${exam.id}`, { status });
    load();
  }

  return (
    <div>
      <div className="topbar">
        <h2>مدیریت آزمون‌ها</h2>
        {hasPermission("create") && (
          <button onClick={() => setShowForm((s) => !s)}>{showForm ? "بستن فرم" : "+ آزمون جدید"}</button>
        )}
      </div>

      {showForm && (
        <form className="card" onSubmit={submit} style={{ marginBottom: 20, display: "grid", gap: 12, gridTemplateColumns: "1fr 1fr" }}>
          <div className="field"><label>عنوان آزمون</label><input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
          <div className="field"><label>کد آزمون</label><input required value={form.exam_code} onChange={(e) => setForm({ ...form, exam_code: e.target.value })} /></div>
          <div className="field"><label>تاریخ آزمون</label><input required type="date" value={form.exam_date} onChange={(e) => setForm({ ...form, exam_date: e.target.value })} /></div>
          <div className="field"><label>نمره کل</label><input required type="number" value={form.total_score} onChange={(e) => setForm({ ...form, total_score: e.target.value })} /></div>
          <div className="field"><label>حداقل نمره قبولی</label><input required type="number" value={form.passing_score} onChange={(e) => setForm({ ...form, passing_score: e.target.value })} /></div>
          <div className="field" style={{ gridColumn: "1 / -1" }}><label>توضیحات</label><textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
          {error && <div className="error-text" style={{ gridColumn: "1 / -1" }}>{error}</div>}
          <button type="submit" style={{ gridColumn: "1 / -1" }}>ثبت آزمون</button>
        </form>
      )}

      <div className="card">
        <table>
          <thead><tr><th>عنوان</th><th>کد</th><th>تاریخ</th><th>نمره قبولی</th><th>وضعیت</th><th>عملیات</th></tr></thead>
          <tbody>
            {exams.map((exam) => (
              <tr key={exam.id}>
                <td>{exam.title}</td>
                <td>{exam.exam_code}</td>
                <td>{new Date(exam.exam_date).toLocaleDateString("fa-IR")}</td>
                <td>{exam.passing_score} / {exam.total_score}</td>
                <td><span className="badge badge-gold">{STATUS_LABELS[exam.status] || exam.status}</span></td>
                <td>
                  {hasPermission("edit") && (
                    <select value={exam.status} onChange={(e) => updateStatus(exam, e.target.value)}>
                      {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                    </select>
                  )}
                </td>
              </tr>
            ))}
            {exams.length === 0 && <tr><td colSpan={6} style={{ textAlign: "center", color: "#888" }}>آزمونی ثبت نشده است</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

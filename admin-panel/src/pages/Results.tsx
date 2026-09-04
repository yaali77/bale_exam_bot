import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

interface Exam { id: string; title: string; exam_code: string; }
interface Result {
  id: string; user_id: string; exam_id: string; score: string;
  is_passed: boolean | null; status: string; published_at: string | null;
}

const STATUS_LABELS: Record<string, string> = {
  recorded: "ثبت‌شده", reviewed: "بررسی‌شده", published: "منتشرشده", voided: "ابطال‌شده",
};

export default function Results() {
  const { hasPermission } = useAuth();
  const [exams, setExams] = useState<Exam[]>([]);
  const [selectedExam, setSelectedExam] = useState<string>("");
  const [results, setResults] = useState<Result[]>([]);
  const [nationalCode, setNationalCode] = useState("");
  const [score, setScore] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [importSummary, setImportSummary] = useState<string | null>(null);

  useEffect(() => { api.get<Exam[]>("/api/exams").then(setExams); }, []);

  function loadResults(examId: string) {
    setSelectedExam(examId);
    if (!examId) { setResults([]); return; }
    api.get<Result[]>(`/api/results?exam_id=${examId}`).then(setResults);
  }

  async function submitScore(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/api/results", { user_national_code: nationalCode, exam_id: selectedExam, score });
      setNationalCode(""); setScore("");
      loadResults(selectedExam);
    } catch (err: any) { setError(err.message); }
  }

  async function publish(resultId: string) {
    await api.post(`/api/results/${resultId}/publish`);
    loadResults(selectedExam);
  }

  async function publishAll() {
    await api.post(`/api/results/publish-bulk?exam_id=${selectedExam}`);
    loadResults(selectedExam);
  }

  async function uploadExcel(e: React.FormEvent) {
    e.preventDefault();
    if (!excelFile || !selectedExam) return;
    const form = new FormData();
    form.append("file", excelFile);
    const res = await api.postForm<{ total_rows: number; success_count: number; error_count: number }>(
      `/api/excel/import-scores?exam_id=${selectedExam}`, form
    );
    setImportSummary(`از ${res.total_rows} سطر، ${res.success_count} موفق و ${res.error_count} ناموفق بود.`);
    loadResults(selectedExam);
  }

  return (
    <div>
      <div className="topbar"><h2>مدیریت نمرات</h2></div>

      <div className="toolbar">
        <select value={selectedExam} onChange={(e) => loadResults(e.target.value)}>
          <option value="">-- انتخاب آزمون --</option>
          {exams.map((ex) => <option key={ex.id} value={ex.id}>{ex.title} ({ex.exam_code})</option>)}
        </select>
        {selectedExam && hasPermission("publish") && (
          <button className="accent" onClick={publishAll}>انتشار گروهی نتایج این آزمون</button>
        )}
      </div>

      {selectedExam && hasPermission("create") && (
        <div className="card" style={{ marginBottom: 16 }}>
          <form onSubmit={submitScore} style={{ display: "flex", gap: 10, alignItems: "flex-end" }}>
            <div className="field" style={{ margin: 0 }}>
              <label>کد ملی کاربر</label>
              <input required value={nationalCode} onChange={(e) => setNationalCode(e.target.value)} />
            </div>
            <div className="field" style={{ margin: 0 }}>
              <label>نمره</label>
              <input required type="number" step="0.01" value={score} onChange={(e) => setScore(e.target.value)} />
            </div>
            <button type="submit">ثبت نمره</button>
          </form>
          {error && <div className="error-text">{error}</div>}

          <form onSubmit={uploadExcel} style={{ display: "flex", gap: 10, alignItems: "flex-end", marginTop: 16, borderTop: "1px solid #eee", paddingTop: 16 }}>
            <div className="field" style={{ margin: 0 }}>
              <label>ورود گروهی از اکسل (ستون‌ها: national_code, score)</label>
              <input type="file" accept=".xlsx,.xls" onChange={(e) => setExcelFile(e.target.files?.[0] || null)} />
            </div>
            <button type="submit" className="secondary">آپلود اکسل</button>
          </form>
          {importSummary && <p style={{ marginTop: 8, fontSize: 13 }}>{importSummary}</p>}
        </div>
      )}

      <div className="card">
        <table>
          <thead><tr><th>نمره</th><th>وضعیت قبولی</th><th>وضعیت انتشار</th><th>تاریخ انتشار</th><th>عملیات</th></tr></thead>
          <tbody>
            {results.map((r) => (
              <tr key={r.id}>
                <td>{r.score}</td>
                <td><span className={`badge ${r.is_passed ? "badge-green" : "badge-red"}`}>{r.is_passed ? "قبول" : "مردود"}</span></td>
                <td><span className="badge badge-gray">{STATUS_LABELS[r.status] || r.status}</span></td>
                <td>{r.published_at ? new Date(r.published_at).toLocaleDateString("fa-IR") : "-"}</td>
                <td>
                  {r.status !== "published" && hasPermission("publish") && (
                    <button className="secondary" onClick={() => publish(r.id)}>انتشار</button>
                  )}
                </td>
              </tr>
            ))}
            {selectedExam && results.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "#888" }}>نمره‌ای ثبت نشده است</td></tr>}
            {!selectedExam && <tr><td colSpan={5} style={{ textAlign: "center", color: "#888" }}>ابتدا یک آزمون انتخاب کنید</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

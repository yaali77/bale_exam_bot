import React, { useEffect, useState } from "react";
import { api } from "../api/client";

interface AdminUser { id: string; username: string; full_name: string; role: string; is_active: boolean; }

const ROLE_LABELS: Record<string, string> = {
  super_admin: "Super Admin", system_manager: "مدیر سامانه", exam_manager: "مدیر آزمون",
  score_operator: "اپراتور ثبت نمره", user_operator: "اپراتور کاربران", support: "پشتیبان", observer: "ناظر",
};

export default function Admins() {
  const [admins, setAdmins] = useState<AdminUser[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ username: "", full_name: "", password: "", role: "observer" });
  const [error, setError] = useState<string | null>(null);

  function load() { api.get<AdminUser[]>("/api/admins").then(setAdmins); }
  useEffect(load, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/api/admins", form);
      setShowForm(false);
      setForm({ username: "", full_name: "", password: "", role: "observer" });
      load();
    } catch (err: any) { setError(err.message); }
  }

  async function toggleActive(admin: AdminUser) {
    await api.patch(`/api/admins/${admin.id}`, { is_active: !admin.is_active });
    load();
  }

  return (
    <div>
      <div className="topbar">
        <h2>مدیریت ادمین‌ها و نقش‌ها</h2>
        <button onClick={() => setShowForm((s) => !s)}>{showForm ? "بستن" : "+ ادمین جدید"}</button>
      </div>

      {showForm && (
        <form className="card" onSubmit={submit} style={{ marginBottom: 20, display: "grid", gap: 12, gridTemplateColumns: "1fr 1fr" }}>
          <div className="field"><label>نام کاربری</label><input required value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></div>
          <div className="field"><label>نام کامل</label><input required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></div>
          <div className="field"><label>رمز عبور</label><input required type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></div>
          <div className="field">
            <label>نقش</label>
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              {Object.entries(ROLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          {error && <div className="error-text" style={{ gridColumn: "1 / -1" }}>{error}</div>}
          <button type="submit" style={{ gridColumn: "1 / -1" }}>ایجاد ادمین</button>
        </form>
      )}

      <div className="card">
        <table>
          <thead><tr><th>نام کاربری</th><th>نام کامل</th><th>نقش</th><th>وضعیت</th><th>عملیات</th></tr></thead>
          <tbody>
            {admins.map((a) => (
              <tr key={a.id}>
                <td>{a.username}</td>
                <td>{a.full_name}</td>
                <td><span className="badge badge-gold">{ROLE_LABELS[a.role] || a.role}</span></td>
                <td><span className={`badge ${a.is_active ? "badge-green" : "badge-red"}`}>{a.is_active ? "فعال" : "غیرفعال"}</span></td>
                <td><button className="secondary" onClick={() => toggleActive(a)}>{a.is_active ? "غیرفعال کردن" : "فعال کردن"}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

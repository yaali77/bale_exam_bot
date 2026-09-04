import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

interface User {
  id: string;
  bale_user_id: number;
  phone_number: string;
  national_code: string;
  first_name: string | null;
  last_name: string | null;
  status: "active" | "disabled";
  registered_at: string;
}

export default function Users() {
  const { hasPermission } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  function load(q = "") {
    setLoading(true);
    api
      .get<User[]>(`/api/users${q ? `?search=${encodeURIComponent(q)}` : ""}`)
      .then(setUsers)
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  async function toggleStatus(user: User) {
    const newStatus = user.status === "active" ? "disabled" : "active";
    const updated = await api.patch<User>(`/api/users/${user.id}/status`, { status: newStatus });
    setUsers((prev) => prev.map((u) => (u.id === user.id ? updated : u)));
  }

  async function requestReportCard(userId: string) {
    await api.post(`/api/users/${userId}/report-card`);
    window.open(`/api/users/${userId}/report-card/download`, "_blank");
  }

  return (
    <div>
      <div className="topbar"><h2>مدیریت کاربران</h2></div>

      <div className="toolbar">
        <input
          placeholder="جستجو بر اساس نام، کد ملی یا شماره تلفن..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && load(search)}
        />
        <button className="secondary" onClick={() => load(search)}>جستجو</button>
      </div>

      <div className="card">
        {loading ? (
          <p>در حال بارگذاری...</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>نام</th><th>کد ملی</th><th>شماره تلفن</th><th>تاریخ ثبت‌نام</th><th>وضعیت</th><th>عملیات</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.first_name || "-"} {u.last_name || ""}</td>
                  <td>{u.national_code}</td>
                  <td>{u.phone_number}</td>
                  <td>{new Date(u.registered_at).toLocaleDateString("fa-IR")}</td>
                  <td>
                    <span className={`badge ${u.status === "active" ? "badge-green" : "badge-red"}`}>
                      {u.status === "active" ? "فعال" : "غیرفعال"}
                    </span>
                  </td>
                  <td style={{ display: "flex", gap: 6 }}>
                    {hasPermission("edit") && (
                      <button className="secondary" onClick={() => toggleStatus(u)}>
                        {u.status === "active" ? "غیرفعال کردن" : "فعال کردن"}
                      </button>
                    )}
                    <button className="accent" onClick={() => requestReportCard(u.id)}>کارنامه</button>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr><td colSpan={6} style={{ textAlign: "center", color: "#888" }}>کاربری یافت نشد</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

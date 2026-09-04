import React, { useEffect, useState } from "react";
import { api } from "../api/client";

interface CorrectionRequest {
  id: string; field_name: string; previous_value: string | null;
  requested_value: string; user_note: string | null; status: string; created_at: string;
}

const FIELD_LABELS: Record<string, string> = { first_name: "نام", last_name: "نام خانوادگی", phone_number: "شماره تلفن" };

export default function Corrections() {
  const [items, setItems] = useState<CorrectionRequest[]>([]);

  function load() {
    api.get<CorrectionRequest[]>("/api/corrections?status=pending").then(setItems);
  }
  useEffect(load, []);

  async function review(id: string, status: "approved" | "rejected") {
    await api.post(`/api/corrections/${id}/review`, { status });
    load();
  }

  return (
    <div>
      <div className="topbar"><h2>درخواست‌های اصلاح اطلاعات</h2></div>
      <div className="card">
        <table>
          <thead><tr><th>فیلد</th><th>مقدار قبلی</th><th>مقدار درخواستی</th><th>تاریخ</th><th>عملیات</th></tr></thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id}>
                <td>{FIELD_LABELS[c.field_name] || c.field_name}</td>
                <td>{c.previous_value || "-"}</td>
                <td>{c.requested_value}</td>
                <td>{new Date(c.created_at).toLocaleDateString("fa-IR")}</td>
                <td style={{ display: "flex", gap: 6 }}>
                  <button onClick={() => review(c.id, "approved")}>تایید</button>
                  <button className="danger" onClick={() => review(c.id, "rejected")}>رد</button>
                </td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "#888" }}>درخواست در انتظاری وجود ندارد</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

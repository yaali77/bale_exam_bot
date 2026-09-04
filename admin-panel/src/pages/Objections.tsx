import React, { useEffect, useState } from "react";
import { api } from "../api/client";

interface Objection {
  id: string; result_id: string; description: string; status: string; created_at: string;
}

export default function Objections() {
  const [items, setItems] = useState<Objection[]>([]);
  const [noteMap, setNoteMap] = useState<Record<string, string>>({});
  const [scoreMap, setScoreMap] = useState<Record<string, string>>({});

  function load() {
    api.get<Objection[]>("/api/objections?status=pending").then(setItems);
  }
  useEffect(load, []);

  async function reject(id: string) {
    await api.post(`/api/objections/${id}/review`, { status: "rejected", resolution_note: noteMap[id] || "" });
    load();
  }

  async function approve(id: string) {
    await api.post(`/api/objections/${id}/review`, {
      status: "approved",
      resolution_note: noteMap[id] || "",
      new_score: scoreMap[id] || undefined,
    });
    load();
  }

  return (
    <div>
      <div className="topbar"><h2>اعتراض به نمره</h2></div>
      <div className="card">
        <table>
          <thead><tr><th>شرح اعتراض</th><th>تاریخ</th><th>یادداشت پاسخ</th><th>نمره جدید (در صورت تایید)</th><th>عملیات</th></tr></thead>
          <tbody>
            {items.map((o) => (
              <tr key={o.id}>
                <td style={{ maxWidth: 260 }}>{o.description}</td>
                <td>{new Date(o.created_at).toLocaleDateString("fa-IR")}</td>
                <td><input value={noteMap[o.id] || ""} onChange={(e) => setNoteMap({ ...noteMap, [o.id]: e.target.value })} /></td>
                <td><input type="number" step="0.01" value={scoreMap[o.id] || ""} onChange={(e) => setScoreMap({ ...scoreMap, [o.id]: e.target.value })} /></td>
                <td style={{ display: "flex", gap: 6 }}>
                  <button onClick={() => approve(o.id)}>تایید</button>
                  <button className="danger" onClick={() => reject(o.id)}>رد</button>
                </td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", color: "#888" }}>اعتراض در انتظاری وجود ندارد</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

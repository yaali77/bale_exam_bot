import React, { useEffect, useState } from "react";
import { api } from "../api/client";

interface Feature { id: string; key: string; display_name: string; is_enabled: boolean; }

export default function Features() {
  const [features, setFeatures] = useState<Feature[]>([]);

  function load() {
    api.get<Feature[]>("/api/features").then(setFeatures);
  }
  useEffect(load, []);

  async function toggle(key: string) {
    const updated = await api.patch<Feature>(`/api/features/${key}/toggle`);
    setFeatures((prev) => prev.map((f) => (f.key === key ? updated : f)));
  }

  return (
    <div>
      <div className="topbar"><h2>مدیریت قابلیت‌ها</h2></div>
      <p style={{ color: "#666", marginBottom: 16, fontSize: 14 }}>
        هر قابلیت را بدون نیاز به تغییر کد یا استقرار مجدد، فعال یا غیرفعال کنید.
      </p>
      <div className="stat-grid">
        {features.map((f) => (
          <div key={f.key} className="stat-card" style={{ borderTopColor: f.is_enabled ? "#1b7a3d" : "#b3261e" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 600 }}>{f.display_name}</span>
              <span className={`badge ${f.is_enabled ? "badge-green" : "badge-red"}`}>
                {f.is_enabled ? "🟢 فعال" : "🔴 غیرفعال"}
              </span>
            </div>
            <button className="secondary" style={{ marginTop: 12, width: "100%" }} onClick={() => toggle(f.key)}>
              {f.is_enabled ? "غیرفعال کن" : "فعال کن"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

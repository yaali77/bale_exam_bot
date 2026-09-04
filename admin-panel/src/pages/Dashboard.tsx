import React, { useEffect, useState } from "react";
import { api } from "../api/client";

interface Stats {
  total_users: number;
  active_users: number;
  total_exams: number;
  total_results: number;
  unpublished_results: number;
  pending_correction_requests: number;
  pending_objections: number;
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    api.get<Stats>("/api/dashboard/stats").then(setStats).catch(() => {});
  }, []);

  const items: { label: string; value: number | string }[] = stats
    ? [
        { label: "کل کاربران", value: stats.total_users },
        { label: "کاربران فعال", value: stats.active_users },
        { label: "تعداد آزمون‌ها", value: stats.total_exams },
        { label: "تعداد نتایج", value: stats.total_results },
        { label: "نتایج منتشرنشده", value: stats.unpublished_results },
        { label: "درخواست‌های اصلاح در انتظار", value: stats.pending_correction_requests },
        { label: "اعتراض‌های در انتظار", value: stats.pending_objections },
      ]
    : [];

  return (
    <div>
      <div className="topbar">
        <h2>داشبورد</h2>
      </div>
      <div className="stat-grid">
        {items.map((item) => (
          <div className="stat-card" key={item.label}>
            <div className="value">{item.value}</div>
            <div className="label">{item.label}</div>
          </div>
        ))}
      </div>
      {!stats && <div className="card">در حال بارگذاری آمار...</div>}
    </div>
  );
}

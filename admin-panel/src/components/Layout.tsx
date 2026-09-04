import React from "react";
import { NavLink, Outlet, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV_ITEMS = [
  { to: "/", label: "داشبورد", permission: "view" },
  { to: "/users", label: "کاربران", permission: "view" },
  { to: "/exams", label: "آزمون‌ها", permission: "view" },
  { to: "/results", label: "نمرات", permission: "view" },
  { to: "/corrections", label: "درخواست‌های اصلاح", permission: "view" },
  { to: "/objections", label: "اعتراض‌ها", permission: "view" },
  { to: "/notifications", label: "اطلاع‌رسانی", permission: "publish" },
  { to: "/appearance", label: "مدیریت ظاهر", permission: "settings" },
  { to: "/features", label: "مدیریت قابلیت‌ها", permission: "settings" },
  { to: "/admins", label: "مدیران", permission: "settings" },
  { to: "/backups", label: "پشتیبان‌گیری", permission: "settings" },
  { to: "/audit-log", label: "گزارش تغییرات", permission: "report" },
];

export default function Layout() {
  const { admin, loading, logout, hasPermission } = useAuth();

  if (loading) return <div style={{ padding: 40 }}>در حال بارگذاری...</div>;
  if (!admin) return <Navigate to="/login" replace />;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>سامانه اعلام نتایج</h1>
        {NAV_ITEMS.filter((item) => hasPermission(item.permission)).map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            {item.label}
          </NavLink>
        ))}
        <div style={{ marginTop: "auto", paddingTop: 24, fontSize: 13, opacity: 0.85 }}>
          <div>{admin.full_name}</div>
          <div style={{ opacity: 0.7 }}>{admin.role}</div>
          <button className="secondary" style={{ marginTop: 10, color: "white", borderColor: "rgba(255,255,255,0.4)" }} onClick={logout}>
            خروج
          </button>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}

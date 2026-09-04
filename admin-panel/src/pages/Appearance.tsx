import React, { useEffect, useState } from "react";
import { api } from "../api/client";

interface AppearanceSettings {
  system_title: string;
  logo_url: string | null;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  background_color: string;
  font_family: string;
  welcome_message: string | null;
  result_message_template: string | null;
  error_message: string | null;
  help_text: string | null;
}

export default function Appearance() {
  const [form, setForm] = useState<AppearanceSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  function load() {
    api.get<AppearanceSettings>("/api/appearance").then(setForm);
  }
  useEffect(load, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    setSaving(true);
    setSavedMsg(null);
    try {
      const updated = await api.patch<AppearanceSettings>("/api/appearance", form);
      setForm(updated);
      setSavedMsg("✅ تغییرات ذخیره شد.");
    } finally {
      setSaving(false);
    }
  }

  async function resetToDefault() {
    const updated = await api.post<AppearanceSettings>("/api/appearance/reset");
    setForm(updated);
    setSavedMsg("↩️ تنظیمات پیش‌فرض بازگردانی شد.");
  }

  if (!form) return <div>در حال بارگذاری...</div>;

  const update = (field: keyof AppearanceSettings, value: string) => setForm({ ...form, [field]: value });

  return (
    <div>
      <div className="topbar">
        <h2>مدیریت ظاهر</h2>
        <button className="secondary" onClick={resetToDefault}>بازگردانی به پیش‌فرض</button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 20 }}>
        <form className="card" onSubmit={save} style={{ display: "grid", gap: 14 }}>
          <div className="field"><label>عنوان سامانه</label><input value={form.system_title} onChange={(e) => update("system_title", e.target.value)} /></div>
          <div className="field"><label>آدرس لوگو (URL)</label><input value={form.logo_url || ""} onChange={(e) => update("logo_url", e.target.value)} placeholder="https://..." /></div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 10 }}>
            <div className="field"><label>رنگ اصلی</label><input type="color" value={form.primary_color} onChange={(e) => update("primary_color", e.target.value)} /></div>
            <div className="field"><label>رنگ مکمل</label><input type="color" value={form.secondary_color} onChange={(e) => update("secondary_color", e.target.value)} /></div>
            <div className="field"><label>رنگ Accent</label><input type="color" value={form.accent_color} onChange={(e) => update("accent_color", e.target.value)} /></div>
            <div className="field"><label>پس‌زمینه</label><input type="color" value={form.background_color} onChange={(e) => update("background_color", e.target.value)} /></div>
          </div>

          <div className="field"><label>فونت</label><input value={form.font_family} onChange={(e) => update("font_family", e.target.value)} /></div>
          <div className="field"><label>پیام خوش‌آمد بات</label><textarea value={form.welcome_message || ""} onChange={(e) => update("welcome_message", e.target.value)} /></div>
          <div className="field"><label>قالب متن نتیجه (از {"{score}"} و {"{status}"} استفاده کنید)</label><textarea value={form.result_message_template || ""} onChange={(e) => update("result_message_template", e.target.value)} /></div>
          <div className="field"><label>پیام خطا</label><textarea value={form.error_message || ""} onChange={(e) => update("error_message", e.target.value)} /></div>
          <div className="field"><label>متن راهنما</label><textarea value={form.help_text || ""} onChange={(e) => update("help_text", e.target.value)} /></div>

          {savedMsg && <div style={{ color: "#1b7a3d", fontSize: 13 }}>{savedMsg}</div>}
          <button type="submit" disabled={saving}>{saving ? "در حال ذخیره..." : "ذخیره تغییرات"}</button>
        </form>

        {/* پیش‌نمایش زنده */}
        <div className="card" style={{ background: form.background_color }}>
          <p style={{ fontSize: 12, color: "#888", marginBottom: 10 }}>پیش‌نمایش</p>
          <div style={{ background: form.primary_color, color: "white", padding: "12px 16px", borderRadius: 8, marginBottom: 10, fontFamily: form.font_family }}>
            {form.system_title}
          </div>
          <div style={{ background: "white", border: `1px solid ${form.accent_color}`, borderRadius: 8, padding: 12, fontFamily: form.font_family, fontSize: 13 }}>
            {form.welcome_message}
          </div>
          <button style={{ background: form.accent_color, color: "#3a2e05", marginTop: 10, width: "100%" }}>دکمه نمونه</button>
        </div>
      </div>
    </div>
  );
}

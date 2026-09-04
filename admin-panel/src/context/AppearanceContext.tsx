import React, { createContext, useContext, useEffect, useState } from "react";
import { api } from "../api/client";

interface Appearance {
  system_title: string;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  background_color: string;
  font_family: string;
}

const DEFAULTS: Appearance = {
  system_title: "سامانه اعلام نتایج آزمون",
  primary_color: "#0d3b66",
  secondary_color: "#082744",
  accent_color: "#c9a227",
  background_color: "#f7f7f5",
  font_family: "Vazirmatn, IRANSans, Tahoma, sans-serif",
};

const AppearanceContext = createContext<Appearance>(DEFAULTS);

export function AppearanceProvider({ children }: { children: React.ReactNode }) {
  const [appearance, setAppearance] = useState<Appearance>(DEFAULTS);

  useEffect(() => {
    api
      .get<Appearance>("/api/appearance")
      .then((data) => {
        setAppearance(data);
        const root = document.documentElement.style;
        root.setProperty("--color-primary", data.primary_color);
        root.setProperty("--color-primary-dark", data.secondary_color);
        root.setProperty("--color-accent", data.accent_color);
        root.setProperty("--color-bg", data.background_color);
        root.setProperty("--font-main", data.font_family);
        document.title = data.system_title;
      })
      .catch(() => { /* در صورت خطا از پیش‌فرض‌های ثابت theme.css استفاده می‌شود */ });
  }, []);

  return <AppearanceContext.Provider value={appearance}>{children}</AppearanceContext.Provider>;
}

export function useAppearance() {
  return useContext(AppearanceContext);
}

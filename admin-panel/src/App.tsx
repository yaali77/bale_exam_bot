import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { AppearanceProvider } from "./context/AppearanceContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Users from "./pages/Users";
import Exams from "./pages/Exams";
import Results from "./pages/Results";
import Corrections from "./pages/Corrections";
import Objections from "./pages/Objections";
import Notifications from "./pages/Notifications";
import Features from "./pages/Features";
import Appearance from "./pages/Appearance";
import Backups from "./pages/Backups";
import Admins from "./pages/Admins";
import AuditLog from "./pages/AuditLog";

export default function App() {
  return (
    <BrowserRouter>
      <AppearanceProvider>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/users" element={<Users />} />
            <Route path="/exams" element={<Exams />} />
            <Route path="/results" element={<Results />} />
            <Route path="/corrections" element={<Corrections />} />
            <Route path="/objections" element={<Objections />} />
            <Route path="/notifications" element={<Notifications />} />
            <Route path="/features" element={<Features />} />
            <Route path="/appearance" element={<Appearance />} />
            <Route path="/backups" element={<Backups />} />
            <Route path="/admins" element={<Admins />} />
            <Route path="/audit-log" element={<AuditLog />} />
          </Route>
        </Routes>
      </AuthProvider>
      </AppearanceProvider>
    </BrowserRouter>
  );
}

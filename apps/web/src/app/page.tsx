"use client";

import React, { useState, useEffect } from "react";
import {
  Rocket,
  Mail,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Upload,
  Play,
  Pause,
  User,
  Settings,
  Layers,
  ShieldCheck,
  FileText,
  ExternalLink,
  RefreshCw,
  LogOut,
  Key,
  Briefcase,
  Search,
  Filter,
} from "lucide-react";

const DEFAULT_API_URL = "https://mailorbit-api-nrxf.onrender.com";

export default function MailOrbitDashboard() {
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [token, setToken] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"dashboard" | "campaigns" | "contacts" | "ai" | "settings">("dashboard");

  // Auth form state
  const [authMode, setAuthMode] = useState<"login" | "signup">("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // App Data
  const [apiHealthy, setApiHealthy] = useState<boolean | null>(null);
  const [purposes, setPurposes] = useState<any[]>([]);
  const [batches, setBatches] = useState<any[]>([]);
  const [contacts, setContacts] = useState<any[]>([]);
  const [profile, setProfile] = useState<any>(null);
  const [aiKeys, setAiKeys] = useState<any[]>([]);
  const [relays, setRelays] = useState<any[]>([]);
  const [loadingData, setLoadingData] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Job Description Matching State (M8)
  const [jdText, setJdText] = useState("");
  const [jdMatchResult, setJdMatchResult] = useState<any>(null);
  const [jdMatching, setJdMatching] = useState(false);

  // Gemini BYOK Key State (M7)
  const [newGeminiKey, setNewGeminiKey] = useState("");
  const [keyModel, setKeyModel] = useState("gemini-2.5-flash");
  const [keySaving, setKeySaving] = useState(false);

  // Relay Setup State (M5)
  const [relayScriptUrl, setRelayScriptUrl] = useState("");
  const [relayAuthToken, setRelayAuthToken] = useState("");
  const [relayEmail, setRelayEmail] = useState("");
  const [relaySaving, setRelaySaving] = useState(false);

  // CSV Import State
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [importingCsv, setImportingCsv] = useState(false);
  const [importSelectedPurpose, setImportSelectedPurpose] = useState<string>("");

  // New Purpose State
  const [newPurposeName, setNewPurposeName] = useState("");
  const [newPurposeSubject, setNewPurposeSubject] = useState("Quick question regarding {company}");
  const [newPurposeBody, setNewPurposeBody] = useState("Hi {name},\n\nNoticed your leadership at {company}. Would love to share our engineering capabilities.");

  // Auto-Batch Modal
  const [batchSize, setBatchSize] = useState(25);
  const [batchSendTime, setBatchSendTime] = useState("10:00");

  // Load token from localStorage
  useEffect(() => {
    const savedToken = localStorage.getItem("mailorbit_token");
    const savedApi = localStorage.getItem("mailorbit_api_url") || DEFAULT_API_URL;
    setApiUrl(savedApi);
    if (savedToken) {
      setToken(savedToken);
    }
  }, []);

  // Check API health
  const checkHealth = async () => {
    try {
      const res = await fetch(`${apiUrl}/api/v1/health`);
      if (res.ok) {
        setApiHealthy(true);
      } else {
        setApiHealthy(false);
      }
    } catch {
      setApiHealthy(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, [apiUrl]);

  // Load user data when token changes
  useEffect(() => {
    if (token) {
      loadAllData();
    }
  }, [token, apiUrl]);

  const apiFetch = async (endpoint: string, options: RequestInit = {}) => {
    const headers = {
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
    };
    return fetch(`${apiUrl}${endpoint}`, { ...options, headers });
  };

  const loadAllData = async () => {
    if (!token) return;
    setLoadingData(true);
    try {
      const [userRes, profRes, purpRes, batchRes, contRes, aiRes, relayRes] = await Promise.all([
        apiFetch("/api/v1/auth/me"),
        apiFetch("/api/v1/profile"),
        apiFetch("/api/v1/purposes"),
        apiFetch("/api/v1/batches"),
        apiFetch("/api/v1/contacts?limit=100"),
        apiFetch("/api/v1/ai-keys"),
        apiFetch("/api/v1/senders"),
      ]);

      if (userRes.ok) setCurrentUser(await userRes.json());
      if (profRes.ok) setProfile(await profRes.json());
      if (purpRes.ok) {
        const pData = await purpRes.json();
        setPurposes(pData);
        if (pData.length > 0 && !importSelectedPurpose) {
          setImportSelectedPurpose(pData[0].id);
        }
      }
      if (batchRes.ok) setBatches(await batchRes.json());
      if (contRes.ok) setContacts(await contRes.json());
      if (aiRes.ok) setAiKeys(await aiRes.json());
      if (relayRes.ok) setRelays(await relayRes.json());
    } catch (err) {
      console.error("Failed loading data", err);
    } finally {
      setLoadingData(false);
    }
  };

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);
    try {
      const endpoint = authMode === "login" ? "/api/v1/auth/login" : "/api/v1/auth/signup";
      const res = await fetch(`${apiUrl}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authEmail, password: authPassword }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Authentication failed");
      }
      localStorage.setItem("mailorbit_token", data.access_token);
      setToken(data.access_token);
      setAuthEmail("");
      setAuthPassword("");
    } catch (err: any) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("mailorbit_token");
    setToken(null);
    setCurrentUser(null);
  };

  const handleCreatePurpose = async () => {
    if (!newPurposeName.trim()) return;
    try {
      const res = await apiFetch("/api/v1/purposes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newPurposeName,
          default_subject_template: newPurposeSubject,
          default_body_template: newPurposeBody,
        }),
      });
      if (res.ok) {
        setNewPurposeName("");
        loadAllData();
        setStatusMessage("Campaign purpose created successfully!");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleAutoBatch = async (purposeId: string) => {
    try {
      const res = await apiFetch("/api/v1/batches/auto-generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          purpose_id: purposeId,
          batch_size: batchSize,
          daily_send_time: batchSendTime,
          active_days: ["mon", "tue", "wed", "thu", "fri"],
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setStatusMessage(`Auto-generated ${data.created_batches_count} batches (${data.contacts_assigned_count} leads)!`);
        loadAllData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleDispatchBatch = async (batchId: string) => {
    try {
      setStatusMessage("Dispatching batch...");
      const res = await apiFetch(`/api/v1/batches/${batchId}/dispatch`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setStatusMessage(`Batch completed: ${data.sent_count} sent, ${data.replaced_count} auto-topped up, status: ${data.batch_status}`);
        loadAllData();
      } else {
        const err = await res.json();
        setStatusMessage(`Dispatch failed: ${err.detail || "Error"}`);
      }
    } catch (err: any) {
      setStatusMessage(`Error dispatching: ${err.message}`);
    }
  };

  const handleMatchJD = async () => {
    if (!jdText.trim()) return;
    setJdMatching(true);
    try {
      const res = await apiFetch("/api/v1/profile/match-jd", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jd_text: jdText }),
      });
      if (res.ok) {
        setJdMatchResult(await res.json());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setJdMatching(false);
    }
  };

  const handleSaveGeminiKey = async () => {
    if (!newGeminiKey.trim()) return;
    setKeySaving(true);
    try {
      const res = await apiFetch("/api/v1/ai-keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: "gemini",
          api_key: newGeminiKey.trim(),
          model: keyModel,
        }),
      });
      if (res.ok) {
        const newKey = await res.json();
        // Test key immediately
        await apiFetch(`/api/v1/ai-keys/${newKey.id}/test`, { method: "POST" });
        setNewGeminiKey("");
        setStatusMessage("Gemini API key encrypted and verified!");
        loadAllData();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setKeySaving(false);
    }
  };

  const handleSaveRelay = async () => {
    if (!relayScriptUrl.trim() || !relayAuthToken.trim()) return;
    setRelaySaving(true);
    try {
      const res = await apiFetch("/api/v1/senders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: relayEmail.trim() || "outreach@gmail.com",
          relay_type: "APPS_SCRIPT",
          script_url: relayScriptUrl.trim(),
          auth_token: relayAuthToken.trim(),
        }),
      });
      if (res.ok) {
        const relay = await res.json();
        // Test relay
        await apiFetch(`/api/v1/senders/${relay.id}/test`, { method: "POST" });
        setRelayScriptUrl("");
        setRelayAuthToken("");
        setRelayEmail("");
        setStatusMessage("Google Apps Script relay connected and verified!");
        loadAllData();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setRelaySaving(false);
    }
  };

  const handleUploadCsv = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvFile) return;
    setImportingCsv(true);
    try {
      const formData = new FormData();
      formData.append("file", csvFile);
      if (importSelectedPurpose) {
        formData.append("purpose_id", importSelectedPurpose);
      }
      formData.append("auto_batch", "true");
      formData.append("batch_size", batchSize.toString());
      formData.append("daily_send_time", batchSendTime);

      const res = await apiFetch("/api/v1/contacts/import-csv", {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        setStatusMessage(`Imported ${data.summary.imported_count} leads! Auto-created ${data.created_batches_count} batches.`);
        setCsvFile(null);
        loadAllData();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setImportingCsv(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#090d16", color: "#f1f5f9", display: "flex", flexDirection: "column" }}>
      {/* Top Navbar */}
      <header style={{ borderBottom: "1px solid #1e293b", background: "#0f172a", padding: "12px 24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{ background: "linear-gradient(135deg, #0284c7, #38bdf8)", padding: "8px", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Rocket size={20} color="#ffffff" />
          </div>
          <div>
            <span style={{ fontSize: "1.25rem", fontWeight: 700, letterSpacing: "-0.02em", color: "#f8fafc" }}>MailOrbit</span>
            <span style={{ marginLeft: "8px", fontSize: "0.75rem", background: "#1e293b", padding: "2px 8px", borderRadius: "12px", color: "#38bdf8", border: "1px solid #334155" }}>v0.1.0 Cloud</span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          {/* Live API status indicator */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.85rem", background: "#1e293b", padding: "4px 10px", borderRadius: "16px", border: "1px solid #334155" }}>
            <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: apiHealthy ? "#22c55e" : "#ef4444" }} />
            <span style={{ color: apiHealthy ? "#86efac" : "#fca5a5" }}>
              {apiHealthy ? "Render API: Live" : "Render API: Connecting..."}
            </span>
          </div>

          {token && currentUser ? (
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div style={{ fontSize: "0.85rem", color: "#cbd5e1" }}>
                <User size={14} style={{ display: "inline", marginRight: "4px" }} />
                {currentUser.email}
              </div>
              <button
                onClick={handleLogout}
                style={{ background: "#334155", color: "#f8fafc", border: "none", padding: "6px 12px", borderRadius: "6px", cursor: "pointer", display: "flex", alignItems: "center", gap: "6px", fontSize: "0.85rem" }}
              >
                <LogOut size={14} /> Logout
              </button>
            </div>
          ) : (
            <div style={{ fontSize: "0.85rem", color: "#94a3b8" }}>Guest Mode</div>
          )}
        </div>
      </header>

      {/* Status banner */}
      {statusMessage && (
        <div style={{ background: "#0284c7", color: "#ffffff", padding: "8px 24px", fontSize: "0.9rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{statusMessage}</span>
          <button onClick={() => setStatusMessage(null)} style={{ background: "transparent", border: "none", color: "#ffffff", cursor: "pointer", fontWeight: 700 }}>✕</button>
        </div>
      )}

      {/* Main Content Area */}
      <div style={{ display: "flex", flex: 1 }}>
        {/* Left Sidebar Navigation */}
        <aside style={{ width: "240px", borderRight: "1px solid #1e293b", background: "#0b1120", padding: "20px 12px" }}>
          <nav style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <button
              onClick={() => setActiveTab("dashboard")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "10px 14px",
                borderRadius: "6px",
                border: "none",
                background: activeTab === "dashboard" ? "#1e293b" : "transparent",
                color: activeTab === "dashboard" ? "#38bdf8" : "#94a3b8",
                cursor: "pointer",
                fontWeight: activeTab === "dashboard" ? 600 : 400,
                textAlign: "left",
              }}
            >
              <Rocket size={18} /> Overview
            </button>

            <button
              onClick={() => setActiveTab("campaigns")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "10px 14px",
                borderRadius: "6px",
                border: "none",
                background: activeTab === "campaigns" ? "#1e293b" : "transparent",
                color: activeTab === "campaigns" ? "#38bdf8" : "#94a3b8",
                cursor: "pointer",
                fontWeight: activeTab === "campaigns" ? 600 : 400,
                textAlign: "left",
              }}
            >
              <Layers size={18} /> Campaigns & Batches
            </button>

            <button
              onClick={() => setActiveTab("contacts")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "10px 14px",
                borderRadius: "6px",
                border: "none",
                background: activeTab === "contacts" ? "#1e293b" : "transparent",
                color: activeTab === "contacts" ? "#38bdf8" : "#94a3b8",
                cursor: "pointer",
                fontWeight: activeTab === "contacts" ? 600 : 400,
                textAlign: "left",
              }}
            >
              <Mail size={18} /> Leads & CSV Import
            </button>

            <button
              onClick={() => setActiveTab("ai")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "10px 14px",
                borderRadius: "6px",
                border: "none",
                background: activeTab === "ai" ? "#1e293b" : "transparent",
                color: activeTab === "ai" ? "#38bdf8" : "#94a3b8",
                cursor: "pointer",
                fontWeight: activeTab === "ai" ? 600 : 400,
                textAlign: "left",
              }}
            >
              <Sparkles size={18} /> AI Personalizer & JD
            </button>

            <button
              onClick={() => setActiveTab("settings")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "10px 14px",
                borderRadius: "6px",
                border: "none",
                background: activeTab === "settings" ? "#1e293b" : "transparent",
                color: activeTab === "settings" ? "#38bdf8" : "#94a3b8",
                cursor: "pointer",
                fontWeight: activeTab === "settings" ? 600 : 400,
                textAlign: "left",
              }}
            >
              <Settings size={18} /> Sender Relay & Keys
            </button>
          </nav>

          <div style={{ marginTop: "40px", padding: "14px", background: "#111827", borderRadius: "8px", border: "1px solid #1f2937", fontSize: "0.8rem", color: "#9ca3af" }}>
            <div style={{ fontWeight: 600, color: "#e5e7eb", marginBottom: "6px" }}>Connected Stack</div>
            <div>• Neon PostgreSQL (Ohio)</div>
            <div>• Render Cloud API</div>
            <div>• UptimeRobot Keepalive</div>
            <div>• cron-job.org 5m Tick</div>
            <div>• Cloudinary Attachments</div>
          </div>
        </aside>

        {/* Main Tab Views */}
        <main style={{ flex: 1, padding: "32px", overflowY: "auto" }}>
          {!token ? (
            /* Authentication Card if not logged in */
            <div style={{ maxWidth: "420px", margin: "40px auto", background: "#111827", padding: "32px", borderRadius: "12px", border: "1px solid #1f2937" }}>
              <div style={{ textAlign: "center", marginBottom: "24px" }}>
                <Rocket size={36} color="#38bdf8" style={{ margin: "0 auto" }} />
                <h2 style={{ fontSize: "1.5rem", fontWeight: 700, margin: "12px 0 4px" }}>Welcome to MailOrbit</h2>
                <p style={{ color: "#9ca3af", fontSize: "0.9rem", margin: 0 }}>
                  Log in or create an account to start autonomous outreach.
                </p>
              </div>

              <div style={{ display: "flex", borderBottom: "1px solid #1f2937", marginBottom: "20px" }}>
                <button
                  onClick={() => setAuthMode("login")}
                  style={{
                    flex: 1,
                    padding: "8px",
                    background: "transparent",
                    border: "none",
                    borderBottom: authMode === "login" ? "2px solid #38bdf8" : "none",
                    color: authMode === "login" ? "#38bdf8" : "#9ca3af",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Log In
                </button>
                <button
                  onClick={() => setAuthMode("signup")}
                  style={{
                    flex: 1,
                    padding: "8px",
                    background: "transparent",
                    border: "none",
                    borderBottom: authMode === "signup" ? "2px solid #38bdf8" : "none",
                    color: authMode === "signup" ? "#38bdf8" : "#9ca3af",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Sign Up
                </button>
              </div>

              {authError && (
                <div style={{ background: "#7f1d1d", color: "#fecaca", padding: "10px", borderRadius: "6px", fontSize: "0.85rem", marginBottom: "16px" }}>
                  {authError}
                </div>
              )}

              <form onSubmit={handleAuth} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.85rem", color: "#9ca3af", marginBottom: "6px" }}>Email</label>
                  <input
                    type="email"
                    required
                    value={authEmail}
                    onChange={(e) => setAuthEmail(e.target.value)}
                    placeholder="founder@example.com"
                    style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box" }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.85rem", color: "#9ca3af", marginBottom: "6px" }}>Password</label>
                  <input
                    type="password"
                    required
                    value={authPassword}
                    onChange={(e) => setAuthPassword(e.target.value)}
                    placeholder="••••••••••••"
                    style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box" }}
                  />
                </div>
                <button
                  type="submit"
                  disabled={authLoading}
                  style={{
                    background: "#0284c7",
                    color: "#ffffff",
                    border: "none",
                    padding: "12px",
                    borderRadius: "6px",
                    fontWeight: 600,
                    cursor: authLoading ? "not-allowed" : "pointer",
                    marginTop: "8px",
                  }}
                >
                  {authLoading ? "Processing..." : authMode === "login" ? "Sign In" : "Create Account"}
                </button>
              </form>
            </div>
          ) : (
            /* Authenticated Application Views */
            <>
              {activeTab === "dashboard" && (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
                    <div>
                      <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: 0 }}>Outreach Dashboard</h1>
                      <p style={{ color: "#94a3b8", fontSize: "0.95rem", margin: "4px 0 0" }}>
                        Autonomous batching engine running on Neon & Render.
                      </p>
                    </div>
                    <button
                      onClick={loadAllData}
                      style={{ display: "flex", alignItems: "center", gap: "6px", background: "#1e293b", color: "#f8fafc", border: "1px solid #334155", padding: "8px 14px", borderRadius: "6px", cursor: "pointer", fontSize: "0.85rem" }}
                    >
                      <RefreshCw size={14} className={loadingData ? "spin" : ""} /> Refresh
                    </button>
                  </div>

                  {/* Stat Cards */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "32px" }}>
                    <div style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937" }}>
                      <div style={{ color: "#9ca3af", fontSize: "0.85rem", marginBottom: "8px" }}>Total Contacts</div>
                      <div style={{ fontSize: "2rem", fontWeight: 700, color: "#38bdf8" }}>{contacts.length}</div>
                    </div>
                    <div style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937" }}>
                      <div style={{ color: "#9ca3af", fontSize: "0.85rem", marginBottom: "8px" }}>Daily Batches</div>
                      <div style={{ fontSize: "2rem", fontWeight: 700, color: "#4ade80" }}>{batches.length}</div>
                    </div>
                    <div style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937" }}>
                      <div style={{ color: "#9ca3af", fontSize: "0.85rem", marginBottom: "8px" }}>Emails Dispatched</div>
                      <div style={{ fontSize: "2rem", fontWeight: 700, color: "#a855f7" }}>
                        {contacts.filter((c) => c.status === "SENT").length}
                      </div>
                    </div>
                    <div style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937" }}>
                      <div style={{ color: "#9ca3af", fontSize: "0.85rem", marginBottom: "8px" }}>Safety Inactive / DNC</div>
                      <div style={{ fontSize: "2rem", fontWeight: 700, color: "#f87171" }}>
                        {contacts.filter((c) => ["INACTIVE", "UNSUBSCRIBED"].includes(c.status)).length}
                      </div>
                    </div>
                  </div>

                  {/* Active Batches Section */}
                  <div style={{ background: "#111827", padding: "24px", borderRadius: "10px", border: "1px solid #1f2937", marginBottom: "32px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                      <h2 style={{ fontSize: "1.2rem", fontWeight: 600, margin: 0 }}>Upcoming & Active Batches</h2>
                      <button
                        onClick={() => setActiveTab("campaigns")}
                        style={{ background: "#0284c7", color: "#ffffff", border: "none", padding: "6px 14px", borderRadius: "6px", cursor: "pointer", fontSize: "0.85rem", fontWeight: 600 }}
                      >
                        Manage Batches
                      </button>
                    </div>

                    {batches.length === 0 ? (
                      <div style={{ color: "#9ca3af", fontSize: "0.9rem", textAlign: "center", padding: "32px 0" }}>
                        No batches configured yet. Import a CSV or click &quot;Auto-Generate Batches&quot; in Campaigns!
                      </div>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                        {batches.slice(0, 5).map((b) => (
                          <div key={b.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#1f2937", padding: "14px 18px", borderRadius: "8px" }}>
                            <div>
                              <div style={{ fontWeight: 600, color: "#f8fafc" }}>{b.name}</div>
                              <div style={{ fontSize: "0.8rem", color: "#9ca3af" }}>
                                {b.size} leads • Scheduled {b.scheduled_time} ({b.scheduled_days?.join(", ")})
                              </div>
                            </div>
                            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                              <span style={{
                                fontSize: "0.75rem",
                                padding: "4px 10px",
                                borderRadius: "12px",
                                background: b.status === "COMPLETED" ? "#14532d" : b.status === "PAUSED" ? "#7f1d1d" : "#075985",
                                color: b.status === "COMPLETED" ? "#86efac" : b.status === "PAUSED" ? "#fca5a5" : "#7dd3fc",
                                fontWeight: 600,
                              }}>
                                {b.status}
                              </span>
                              {b.status !== "COMPLETED" && (
                                <button
                                  onClick={() => handleDispatchBatch(b.id)}
                                  style={{ background: "#22c55e", color: "#ffffff", border: "none", padding: "6px 12px", borderRadius: "6px", cursor: "pointer", display: "flex", alignItems: "center", gap: "4px", fontSize: "0.8rem", fontWeight: 600 }}
                                >
                                  <Play size={12} /> Dispatch Now
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Campaigns & Batches Tab */}
              {activeTab === "campaigns" && (
                <div>
                  <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 8px" }}>Campaign Purposes & Batches</h1>
                  <p style={{ color: "#94a3b8", fontSize: "0.95rem", margin: "0 0 24px" }}>
                    Configure target purposes (Job Hunt, Pitch) and auto-slice contacts into daily batches.
                  </p>

                  {/* Create Purpose Section */}
                  <div style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937", marginBottom: "28px" }}>
                    <h3 style={{ margin: "0 0 16px", fontSize: "1.1rem" }}>Create New Campaign Purpose</h3>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "14px" }}>
                      <div>
                        <label style={{ display: "block", fontSize: "0.85rem", color: "#9ca3af", marginBottom: "4px" }}>Purpose Name</label>
                        <input
                          type="text"
                          value={newPurposeName}
                          onChange={(e) => setNewPurposeName(e.target.value)}
                          placeholder="e.g. Senior Backend Job Application"
                          style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box" }}
                        />
                      </div>
                      <div>
                        <label style={{ display: "block", fontSize: "0.85rem", color: "#9ca3af", marginBottom: "4px" }}>Subject Template</label>
                        <input
                          type="text"
                          value={newPurposeSubject}
                          onChange={(e) => setNewPurposeSubject(e.target.value)}
                          style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box" }}
                        />
                      </div>
                    </div>
                    <div style={{ marginBottom: "14px" }}>
                      <label style={{ display: "block", fontSize: "0.85rem", color: "#9ca3af", marginBottom: "4px" }}>Body Template</label>
                      <textarea
                        rows={3}
                        value={newPurposeBody}
                        onChange={(e) => setNewPurposeBody(e.target.value)}
                        style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box", fontFamily: "inherit" }}
                      />
                    </div>
                    <button
                      onClick={handleCreatePurpose}
                      style={{ background: "#0284c7", color: "#ffffff", border: "none", padding: "10px 18px", borderRadius: "6px", cursor: "pointer", fontWeight: 600 }}
                    >
                      Save Campaign Purpose
                    </button>
                  </div>

                  {/* Purposes List */}
                  <div style={{ marginBottom: "32px" }}>
                    <h3 style={{ margin: "0 0 16px", fontSize: "1.1rem" }}>Active Purposes</h3>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "16px" }}>
                      {purposes.map((p) => (
                        <div key={p.id} style={{ background: "#111827", padding: "18px", borderRadius: "8px", border: "1px solid #1f2937" }}>
                          <div style={{ fontWeight: 600, fontSize: "1.1rem", color: "#38bdf8", marginBottom: "6px" }}>{p.name}</div>
                          <div style={{ fontSize: "0.85rem", color: "#9ca3af", marginBottom: "12px" }}>
                            Subject: {p.default_subject_template}
                          </div>
                          <button
                            onClick={() => handleAutoBatch(p.id)}
                            style={{ background: "#1e293b", color: "#38bdf8", border: "1px solid #0284c7", padding: "6px 12px", borderRadius: "6px", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600 }}
                          >
                            Auto-Slice Batches (25/day)
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Leads & CSV Import Tab */}
              {activeTab === "contacts" && (
                <div>
                  <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 8px" }}>Leads & CSV Import</h1>
                  <p style={{ color: "#94a3b8", fontSize: "0.95rem", margin: "0 0 24px" }}>
                    Import CSV contacts with automated column normalization and deduplication.
                  </p>

                  {/* CSV Upload Card */}
                  <form onSubmit={handleUploadCsv} style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937", marginBottom: "28px" }}>
                    <h3 style={{ margin: "0 0 14px", fontSize: "1.1rem" }}>Upload CSV Leads</h3>
                    <div style={{ display: "flex", gap: "16px", alignItems: "center", marginBottom: "14px" }}>
                      <input
                        type="file"
                        accept=".csv"
                        onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
                        style={{ color: "#9ca3af" }}
                      />
                      {purposes.length > 0 && (
                        <select
                          value={importSelectedPurpose}
                          onChange={(e) => setImportSelectedPurpose(e.target.value)}
                          style={{ padding: "8px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff" }}
                        >
                          {purposes.map((p) => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                          ))}
                        </select>
                      )}
                      <button
                        type="submit"
                        disabled={!csvFile || importingCsv}
                        style={{
                          background: "#0284c7",
                          color: "#ffffff",
                          border: "none",
                          padding: "10px 18px",
                          borderRadius: "6px",
                          cursor: !csvFile || importingCsv ? "not-allowed" : "pointer",
                          fontWeight: 600,
                        }}
                      >
                        {importingCsv ? "Importing & Auto-batching..." : "Upload & Auto-Batch"}
                      </button>
                    </div>
                  </form>

                  {/* Contacts Table */}
                  <div style={{ background: "#111827", borderRadius: "10px", border: "1px solid #1f2937", overflow: "hidden" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
                      <thead>
                        <tr style={{ background: "#1e293b", borderBottom: "1px solid #334155", color: "#94a3b8", textAlign: "left" }}>
                          <th style={{ padding: "12px 16px" }}>Email</th>
                          <th style={{ padding: "12px 16px" }}>Name</th>
                          <th style={{ padding: "12px 16px" }}>Company</th>
                          <th style={{ padding: "12px 16px" }}>Role</th>
                          <th style={{ padding: "12px 16px" }}>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {contacts.map((c) => (
                          <tr key={c.id} style={{ borderBottom: "1px solid #1f2937" }}>
                            <td style={{ padding: "12px 16px", color: "#f8fafc" }}>{c.email}</td>
                            <td style={{ padding: "12px 16px", color: "#cbd5e1" }}>{c.name || "—"}</td>
                            <td style={{ padding: "12px 16px", color: "#cbd5e1" }}>{c.company || "—"}</td>
                            <td style={{ padding: "12px 16px", color: "#cbd5e1" }}>{c.role || "—"}</td>
                            <td style={{ padding: "12px 16px" }}>
                              <span style={{
                                padding: "2px 8px",
                                borderRadius: "12px",
                                fontSize: "0.75rem",
                                fontWeight: 600,
                                background: c.status === "SENT" ? "#14532d" : c.status === "PENDING" ? "#075985" : "#7f1d1d",
                                color: c.status === "SENT" ? "#86efac" : c.status === "PENDING" ? "#7dd3fc" : "#fca5a5",
                              }}>
                                {c.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* AI Personalization & JD Matching Tab (M7 & M8) */}
              {activeTab === "ai" && (
                <div>
                  <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 8px" }}>AI Personalizer & Job Description Matcher</h1>
                  <p style={{ color: "#94a3b8", fontSize: "0.95rem", margin: "0 0 24px" }}>
                    Configure Gemini BYOK keys and test real-time technical keyword alignment with job postings.
                  </p>

                  {/* JD Matcher Engine Card (M8) */}
                  <div style={{ background: "#111827", padding: "24px", borderRadius: "10px", border: "1px solid #1f2937", marginBottom: "32px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
                      <Briefcase size={20} color="#38bdf8" />
                      <h3 style={{ margin: 0, fontSize: "1.15rem" }}>Live Job Description Keyword Matcher (Milestone M8)</h3>
                    </div>
                    <textarea
                      rows={4}
                      value={jdText}
                      onChange={(e) => setJdText(e.target.value)}
                      placeholder="Paste Job Description text here (e.g. 'Looking for a Senior Software Engineer with Python, FastAPI, Next.js, and PostgreSQL')..."
                      style={{ width: "100%", padding: "12px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box", fontFamily: "inherit", marginBottom: "14px" }}
                    />
                    <button
                      onClick={handleMatchJD}
                      disabled={jdMatching || !jdText.trim()}
                      style={{ background: "#0284c7", color: "#ffffff", border: "none", padding: "10px 20px", borderRadius: "6px", cursor: jdMatching ? "not-allowed" : "pointer", fontWeight: 600 }}
                    >
                      {jdMatching ? "Analyzing..." : "Scan & Calculate Match"}
                    </button>

                    {jdMatchResult && (
                      <div style={{ marginTop: "20px", padding: "18px", background: "#1e293b", borderRadius: "8px", border: "1px solid #334155" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "12px" }}>
                          <div style={{ fontSize: "2rem", fontWeight: 700, color: jdMatchResult.match_score >= 70 ? "#4ade80" : "#facc15" }}>
                            {jdMatchResult.match_score}%
                          </div>
                          <div>
                            <div style={{ fontWeight: 600, color: "#f8fafc" }}>Technical Alignment Score</div>
                            <div style={{ fontSize: "0.85rem", color: "#94a3b8" }}>{jdMatchResult.pitch_angle}</div>
                          </div>
                        </div>

                        <div style={{ marginBottom: "10px" }}>
                          <span style={{ fontSize: "0.8rem", color: "#9ca3af", marginRight: "8px" }}>Matched Skills:</span>
                          {jdMatchResult.matched_skills.map((s: string) => (
                            <span key={s} style={{ background: "#14532d", color: "#86efac", padding: "3px 8px", borderRadius: "12px", fontSize: "0.75rem", marginRight: "6px", fontWeight: 600 }}>
                              {s}
                            </span>
                          ))}
                        </div>

                        <div>
                          <span style={{ fontSize: "0.8rem", color: "#9ca3af", marginRight: "8px" }}>Missing / Opportunity Skills:</span>
                          {jdMatchResult.missing_skills.map((s: string) => (
                            <span key={s} style={{ background: "#78350f", color: "#fcd34d", padding: "3px 8px", borderRadius: "12px", fontSize: "0.75rem", marginRight: "6px", fontWeight: 600 }}>
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Gemini BYOK Card (M7) */}
                  <div style={{ background: "#111827", padding: "24px", borderRadius: "10px", border: "1px solid #1f2937" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
                      <Key size={20} color="#38bdf8" />
                      <h3 style={{ margin: 0, fontSize: "1.15rem" }}>Gemini BYOK API Key (Milestone M7)</h3>
                    </div>
                    <div style={{ display: "flex", gap: "14px", alignItems: "center", marginBottom: "14px" }}>
                      <input
                        type="password"
                        value={newGeminiKey}
                        onChange={(e) => setNewGeminiKey(e.target.value)}
                        placeholder="Paste your Gemini API key (AIzaSy...)"
                        style={{ flex: 1, padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff" }}
                      />
                      <select
                        value={keyModel}
                        onChange={(e) => setKeyModel(e.target.value)}
                        style={{ padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff" }}
                      >
                        <option value="gemini-2.5-flash">gemini-2.5-flash (Fast)</option>
                        <option value="gemini-2.5-flash-lite">gemini-2.5-flash-lite (Cost-effective)</option>
                      </select>
                      <button
                        onClick={handleSaveGeminiKey}
                        disabled={keySaving || !newGeminiKey.trim()}
                        style={{ background: "#0284c7", color: "#ffffff", border: "none", padding: "10px 18px", borderRadius: "6px", cursor: keySaving ? "not-allowed" : "pointer", fontWeight: 600 }}
                      >
                        {keySaving ? "Encrypting & Testing..." : "Save Key"}
                      </button>
                    </div>

                    {/* Active keys list */}
                    {aiKeys.map((k) => (
                      <div key={k.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#1e293b", padding: "12px 16px", borderRadius: "8px", marginTop: "10px" }}>
                        <div>
                          <span style={{ fontWeight: 600, color: "#38bdf8" }}>{k.provider}</span> • <span style={{ color: "#cbd5e1" }}>{k.model}</span> • <span style={{ fontFamily: "monospace", color: "#9ca3af" }}>{k.masked_key}</span>
                        </div>
                        <span style={{ background: k.status === "ACTIVE" ? "#14532d" : "#7f1d1d", color: k.status === "ACTIVE" ? "#86efac" : "#fca5a5", padding: "2px 8px", borderRadius: "12px", fontSize: "0.75rem", fontWeight: 600 }}>
                          {k.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Settings & Sender Relay Tab */}
              {activeTab === "settings" && (
                <div>
                  <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 8px" }}>Settings & Google Apps Script Relay</h1>
                  <p style={{ color: "#94a3b8", fontSize: "0.95rem", margin: "0 0 24px" }}>
                    Configure zero-password Google Apps Script relays to dispatch over HTTPS:443.
                  </p>

                  {/* Apps Script Relay Card */}
                  <div style={{ background: "#111827", padding: "24px", borderRadius: "10px", border: "1px solid #1f2937", marginBottom: "28px" }}>
                    <h3 style={{ margin: "0 0 14px", fontSize: "1.15rem" }}>Google Apps Script Relay (HTTPS:443)</h3>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px", marginBottom: "14px" }}>
                      <div>
                        <label style={{ display: "block", fontSize: "0.85rem", color: "#9ca3af", marginBottom: "4px" }}>Sender Email (Gmail / Workspace)</label>
                        <input
                          type="email"
                          value={relayEmail}
                          onChange={(e) => setRelayEmail(e.target.value)}
                          placeholder="your.name@gmail.com"
                          style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box" }}
                        />
                      </div>
                      <div>
                        <label style={{ display: "block", fontSize: "0.85rem", color: "#9ca3af", marginBottom: "4px" }}>Web App URL (from Apps Script Deployment)</label>
                        <input
                          type="url"
                          value={relayScriptUrl}
                          onChange={(e) => setRelayScriptUrl(e.target.value)}
                          placeholder="https://script.google.com/macros/s/.../exec"
                          style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box" }}
                        />
                      </div>
                    </div>
                    <div style={{ marginBottom: "16px" }}>
                      <label style={{ display: "block", fontSize: "0.85rem", color: "#9ca3af", marginBottom: "4px" }}>Secret Auth Token</label>
                      <input
                        type="password"
                        value={relayAuthToken}
                        onChange={(e) => setRelayAuthToken(e.target.value)}
                        placeholder="Secret shared token from script configuration"
                        style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box" }}
                      />
                    </div>
                    <button
                      onClick={handleSaveRelay}
                      disabled={relaySaving || !relayScriptUrl.trim() || !relayAuthToken.trim()}
                      style={{ background: "#0284c7", color: "#ffffff", border: "none", padding: "10px 18px", borderRadius: "6px", cursor: relaySaving ? "not-allowed" : "pointer", fontWeight: 600 }}
                    >
                      {relaySaving ? "Saving & Testing..." : "Connect Relay"}
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}

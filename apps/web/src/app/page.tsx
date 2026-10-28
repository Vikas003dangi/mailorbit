"use client";

import React, { useState, useEffect, useId } from "react";
import {
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
  Crown,
  Database,
  Server,
  Activity,
  Code2,
  Github,
  Linkedin,
  Send,
  Zap,
  Globe,
  Award,
  BookOpen,
  ArrowRight,
  ChevronRight,
  Info,
} from "lucide-react";

const DEFAULT_API_URL = "https://mailorbit-api-nrxf.onrender.com";

// Superuser accounts with full administrative control deck access
const SUPERUSER_EMAILS = ["vikassdangi@gmail.com", "vd19055@gmail.com"];

// Orbital Logo Component
function OrbitalLogo({ size = 36 }: { size?: number }) {
  const gradientId = useId();
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ filter: "drop-shadow(0 0 12px rgba(56, 189, 248, 0.45))" }}
      >
        <defs>
          <linearGradient id={`orbitGrad_${gradientId}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#38bdf8" />
            <stop offset="50%" stopColor="#818cf8" />
            <stop offset="100%" stopColor="#c084fc" />
          </linearGradient>
          <radialGradient id={`coreGrad_${gradientId}`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#67e8f9" />
            <stop offset="40%" stopColor="#0284c7" />
            <stop offset="100%" stopColor="#1e1b4b" />
          </radialGradient>
        </defs>

        {/* Outer Orbital Ring */}
        <ellipse
          cx="50"
          cy="50"
          rx="44"
          ry="16"
          stroke={`url(#orbitGrad_${gradientId})`}
          strokeWidth="2.5"
          strokeDasharray="6 3"
          transform="rotate(-28 50 50)"
          opacity="0.85"
        />

        {/* Inner Counter Orbital Ring */}
        <ellipse
          cx="50"
          cy="50"
          rx="40"
          ry="14"
          stroke="#38bdf8"
          strokeWidth="1.5"
          transform="rotate(35 50 50)"
          opacity="0.55"
        />

        {/* Core Celestial Sphere */}
        <circle cx="50" cy="50" r="17" fill={`url(#coreGrad_${gradientId})`} />
        <circle cx="45" cy="45" r="4" fill="#ffffff" opacity="0.6" />

        {/* Orbiting Satellite Data Nodes */}
        <circle cx="82" cy="36" r="3.5" fill="#38bdf8" />
        <circle cx="16" cy="62" r="2.8" fill="#c084fc" />
        <circle cx="68" cy="74" r="2.5" fill="#818cf8" />
      </svg>
      <div>
        <div style={{ display: "flex", alignItems: "baseline", gap: "2px" }}>
          <span style={{ fontSize: "1.35rem", fontWeight: 800, letterSpacing: "-0.03em", color: "#ffffff" }}>
            Mail
          </span>
          <span
            style={{
              fontSize: "1.35rem",
              fontWeight: 800,
              letterSpacing: "-0.03em",
              background: "linear-gradient(135deg, #38bdf8 0%, #818cf8 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            Orbit
          </span>
        </div>
        <div style={{ fontSize: "0.68rem", color: "#94a3b8", fontWeight: 500, letterSpacing: "0.04em", marginTop: "-2px" }}>
          AUTONOMOUS OUTREACH
        </div>
      </div>
    </div>
  );
}

// Sample Data for Browser Sandbox / Demo Mode
const DEMO_BATCHES = [
  {
    id: "demo-b1",
    batch_number: 1,
    status: "ACTIVE",
    scheduled_date: "Today",
    scheduled_time: "09:30 AM",
    total_contacts: 30,
    sent_count: 24,
    bounced_count: 1,
    replaced_count: 1,
    purpose_name: "Senior AI / Backend Engineer Application",
  },
  {
    id: "demo-b2",
    batch_number: 2,
    status: "SCHEDULED",
    scheduled_date: "Tomorrow",
    scheduled_time: "09:30 AM",
    total_contacts: 30,
    sent_count: 0,
    bounced_count: 0,
    replaced_count: 0,
    purpose_name: "Senior AI / Backend Engineer Application",
  },
  {
    id: "demo-b3",
    batch_number: 3,
    status: "COMPLETED",
    scheduled_date: "Yesterday",
    scheduled_time: "10:00 AM",
    total_contacts: 25,
    sent_count: 25,
    bounced_count: 0,
    replaced_count: 0,
    purpose_name: "Direct Tech Leadership Referral",
  },
  {
    id: "demo-b4",
    batch_number: 4,
    status: "PAUSED",
    scheduled_date: "Friday",
    scheduled_time: "11:00 AM",
    total_contacts: 20,
    sent_count: 0,
    bounced_count: 0,
    replaced_count: 0,
    purpose_name: "Startup CTO Strategic Outreach",
  },
];

const DEMO_CONTACTS = [
  { id: "c1", name: "Priya Sharma", email: "p.sharma@techscale.io", company: "TechScale AI", role: "Talent Acquisition Lead", status: "SENT" },
  { id: "c2", name: "Rahul Verma", email: "rahul.v@innovatenow.dev", company: "InnovateNow", role: "VP of Engineering", status: "SENT" },
  { id: "c3", name: "Ananya Iyer", email: "ananya@finflow.org", company: "FinFlow Systems", role: "Technical Recruiter", status: "QUEUED" },
  { id: "c4", name: "David Miller", email: "d.miller@cloudnative.co", company: "CloudNative Labs", role: "Engineering Director", status: "REPLACED", note: "Auto-replaced bounced lead" },
  { id: "c5", name: "Sneha Patel", email: "sneha.p@hypergrowth.tech", company: "HyperGrowth Data", role: "Head of People", status: "PENDING" },
  { id: "c6", name: "Arjun Mehta", email: "arjun.m@razorflow.com", company: "RazorFlow Payments", role: "Principal Architect", status: "SENT" },
  { id: "c7", name: "Kavita Rao", email: "kavita@nexuscloud.io", company: "NexusCloud", role: "Staff Recruiter", status: "PENDING" },
  { id: "c8", name: "Vikram Malhotra", email: "vikram@omnicompute.ai", company: "OmniCompute", role: "Co-Founder & CTO", status: "QUEUED" },
];

export default function MailOrbitDashboard() {
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [token, setToken] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [isDemoMode, setIsDemoMode] = useState(false);

  // Active Navigation Tab
  const [activeTab, setActiveTab] = useState<
    "overview" | "campaigns" | "contacts" | "ai" | "settings" | "about" | "admin"
  >("overview");

  // Auth form state
  const [authMode, setAuthMode] = useState<"login" | "signup">("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authStatusText, setAuthStatusText] = useState<string | null>(null);

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

  // Superuser Admin Data
  const [adminStats, setAdminStats] = useState<any>(null);
  const [adminSystem, setAdminSystem] = useState<any>(null);
  const [loadingAdmin, setLoadingAdmin] = useState(false);

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
  const [contactSearch, setContactSearch] = useState("");
  const [contactFilter, setContactFilter] = useState("ALL");

  // New Purpose State
  const [newPurposeName, setNewPurposeName] = useState("");
  const [newPurposeSubject, setNewPurposeSubject] = useState("Quick question regarding engineering at {company}");
  const [newPurposeBody, setNewPurposeBody] = useState(
    "Hi {name},\n\nI noticed your engineering leadership at {company}. As a Python & Generative AI engineer specializing in high-throughput architectures and LLM/RAG pipelines, I would love to connect for 5 minutes."
  );

  // Auto-Batch Settings
  const [batchSize, setBatchSize] = useState(30);
  const [batchSendTime, setBatchSendTime] = useState("09:30");

  // Initialize from localStorage and check wake-up health
  useEffect(() => {
    const savedToken = localStorage.getItem("mailorbit_token");
    const savedApi = localStorage.getItem("mailorbit_api_url") || DEFAULT_API_URL;
    const savedDemo = localStorage.getItem("mailorbit_demo") === "true";

    setApiUrl(savedApi);

    if (savedDemo) {
      enableDemoMode();
    } else if (savedToken) {
      setToken(savedToken);
    }

    // Ping health in background to wake up Render container
    wakeUpPing(savedApi);
  }, []);

  const wakeUpPing = async (targetApi: string) => {
    try {
      const res = await fetch(`${targetApi}/api/v1/health`, { method: "GET" });
      if (res.ok) {
        setApiHealthy(true);
      } else {
        setApiHealthy(false);
      }
    } catch {
      setApiHealthy(false);
    }
  };

  const enableDemoMode = () => {
    setIsDemoMode(true);
    setToken("demo_token");
    setCurrentUser({
      id: "demo-user-id",
      email: "demo.engineer@mailorbit.io",
      timezone: "Asia/Kolkata",
      is_superuser: true,
    });
    setBatches(DEMO_BATCHES);
    setContacts(DEMO_CONTACTS);
    setPurposes([
      {
        id: "demo-p1",
        name: "Senior AI / Backend Engineer Application",
        default_subject_template: "Python & GenAI Engineer Profile — {name}",
        default_body_template: "Hi {name},\n\nFollowing your tech team's work at {company}...",
      },
      {
        id: "demo-p2",
        name: "Direct Tech Leadership Referral",
        default_subject_template: "Referral request: Senior Python Engineer",
        default_body_template: "Hi {name},\n\nHope this finds you well. Exploring backend opportunities...",
      },
    ]);
    localStorage.setItem("mailorbit_demo", "true");
  };

  const exitDemoMode = () => {
    setIsDemoMode(false);
    localStorage.removeItem("mailorbit_demo");
    localStorage.removeItem("mailorbit_token");
    setToken(null);
    setCurrentUser(null);
    setBatches([]);
    setContacts([]);
    setPurposes([]);
    setActiveTab("overview");
  };

  // Load user data when token changes
  useEffect(() => {
    if (token && !isDemoMode) {
      loadAllData();
    }
  }, [token, apiUrl, isDemoMode]);

  const apiFetch = async (endpoint: string, options: RequestInit = {}) => {
    if (isDemoMode) {
      return { ok: true, json: async () => ({}) } as Response;
    }
    const headers = {
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
    };
    return fetch(`${apiUrl}${endpoint}`, { ...options, headers });
  };

  const loadAllData = async () => {
    if (!token || isDemoMode) return;
    setLoadingData(true);
    try {
      const [userRes, profRes, purpRes, batchRes, contRes, aiRes, relayRes] = await Promise.all([
        apiFetch("/api/v1/auth/me"),
        apiFetch("/api/v1/profile"),
        apiFetch("/api/v1/purposes"),
        apiFetch("/api/v1/batches"),
        apiFetch("/api/v1/contacts?limit=200"),
        apiFetch("/api/v1/ai-keys"),
        apiFetch("/api/v1/senders"),
      ]);

      if (userRes.ok) {
        const u = await userRes.json();
        // Check superuser
        const isSuper = u.is_superuser || SUPERUSER_EMAILS.includes(u.email.toLowerCase());
        setCurrentUser({ ...u, is_superuser: isSuper });
      }
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

  const loadAdminData = async () => {
    if (isDemoMode) {
      setAdminStats({
        authenticated_as: "demo.engineer@mailorbit.io",
        is_superuser: true,
        timestamp: new Date().toISOString(),
        totals: {
          users: 12,
          batches: 28,
          contacts: 384,
          sender_relays: 8,
          ai_keys: 14,
          attachments: 6,
        },
        contacts_by_status: { SENT: 210, QUEUED: 60, PENDING: 104, BOUNCED: 8, REPLACED: 8 },
        batches_by_status: { ACTIVE: 4, SCHEDULED: 8, COMPLETED: 14, PAUSED: 2 },
      });
      setAdminSystem({
        status: "healthy",
        database: { provider: "Neon Serverless PostgreSQL 16 (Ohio)", connected: true },
        host: { platform: "Render Cloud Container", region: "Oregon / US-West" },
        egress: { protocol: "Google Apps Script HTTPS Relay (443)", circuit_breaker: "10% Batch Safety Pause active" },
      });
      return;
    }

    setLoadingAdmin(true);
    try {
      const [statsRes, sysRes] = await Promise.all([
        apiFetch("/api/v1/admin/stats"),
        apiFetch("/api/v1/admin/system"),
      ]);
      if (statsRes.ok) setAdminStats(await statsRes.json());
      if (sysRes.ok) setAdminSystem(await sysRes.json());
    } catch (err) {
      console.error("Error loading admin data", err);
    } finally {
      setLoadingAdmin(false);
    }
  };

  useEffect(() => {
    if (activeTab === "admin" && (currentUser?.is_superuser || isDemoMode)) {
      loadAdminData();
    }
  }, [activeTab, currentUser, isDemoMode]);

  // Handle Authentication with Automated Exponential Backoff and Honest Error Messaging
  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);
    setAuthStatusText(null);

    const maxRetries = 5;
    const delays = [2000, 4000, 7000, 10000, 15000];

    const endpoint = authMode === "login" ? "/api/v1/auth/login" : "/api/v1/auth/signup";

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        if (attempt > 0) {
          setAuthStatusText(
            `Connecting to MailOrbit cloud (attempt ${attempt}/${maxRetries})... Server is waking up from sleep.`
          );
        }

        const res = await fetch(`${apiUrl}${endpoint}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: authEmail.trim(), password: authPassword }),
        });

        const data = await res.json();

        if (!res.ok) {
          if (res.status === 404) {
            throw new Error("No account found with this email. Please switch to the 'Sign Up' tab to create your account.");
          } else if (res.status === 401) {
            throw new Error("Incorrect password. Please verify your credentials and try again.");
          } else if (res.status === 409) {
            throw new Error("An account with this email already exists. Please switch to the 'Log In' tab.");
          } else {
            throw new Error(data.detail || "Authentication request failed.");
          }
        }

        // Login / Signup succeeded
        setAuthStatusText("Authenticated successfully! Loading your dashboard...");
        localStorage.setItem("mailorbit_token", data.access_token);
        localStorage.removeItem("mailorbit_demo");
        setIsDemoMode(false);
        setToken(data.access_token);

        const isSuper =
          data.user?.is_superuser || SUPERUSER_EMAILS.includes(data.user?.email?.toLowerCase());
        setCurrentUser({ ...data.user, is_superuser: isSuper });

        setAuthEmail("");
        setAuthPassword("");
        setAuthStatusText(null);
        setAuthLoading(false);
        return;
      } catch (err: any) {
        const isNetworkError =
          err.name === "TypeError" ||
          err.message.includes("Failed to fetch") ||
          err.message.includes("NetworkError") ||
          err.message.includes("network");

        if (isNetworkError && attempt < maxRetries) {
          const waitTime = delays[attempt] / 1000;
          setAuthStatusText(
            `Render cloud container is spinning up (free-tier cold-start). Retrying in ${waitTime}s...`
          );
          await new Promise((resolve) => setTimeout(resolve, delays[attempt]));
        } else {
          setAuthError(err.message || "An unexpected error occurred.");
          setAuthStatusText(null);
          setAuthLoading(false);
          return;
        }
      }
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("mailorbit_token");
    localStorage.removeItem("mailorbit_demo");
    setToken(null);
    setCurrentUser(null);
    setIsDemoMode(false);
    setActiveTab("overview");
  };

  const handleCreatePurpose = async () => {
    if (!newPurposeName.trim()) return;

    if (isDemoMode) {
      const mockP = {
        id: `demo-p-${Date.now()}`,
        name: newPurposeName.trim(),
        default_subject_template: newPurposeSubject,
        default_body_template: newPurposeBody,
      };
      setPurposes([...purposes, mockP]);
      setNewPurposeName("");
      setStatusMessage("[DEMO] Campaign purpose created successfully!");
      return;
    }

    try {
      const res = await apiFetch("/api/v1/purposes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newPurposeName.trim(),
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
    if (isDemoMode) {
      setStatusMessage(`[DEMO] Auto-generated 2 new batches of 30 leads each for tomorrow and Friday!`);
      return;
    }

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
        setStatusMessage(
          `Auto-generated ${data.created_batches_count} batches (${data.contacts_assigned_count} leads)!`
        );
        loadAllData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleDispatchBatch = async (batchId: string) => {
    if (isDemoMode) {
      setStatusMessage("[DEMO] Simulating live dispatch over Google Apps Script Relay...");
      setTimeout(() => {
        setBatches(
          batches.map((b) => (b.id === batchId ? { ...b, status: "COMPLETED", sent_count: b.total_contacts } : b))
        );
        setStatusMessage("[DEMO] Batch dispatched successfully! 30 emails delivered to test addresses.");
      }, 1500);
      return;
    }

    try {
      setStatusMessage("Dispatching batch via Google Apps Script Relay...");
      const res = await apiFetch(`/api/v1/batches/${batchId}/dispatch`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setStatusMessage(
          `Batch dispatched: ${data.sent_count} sent, ${data.bounced_count} bounced, ${data.replaced_count} replaced.`
        );
        loadAllData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleUploadCsv = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvFile) return;

    if (isDemoMode) {
      setImportingCsv(true);
      setTimeout(() => {
        setImportingCsv(false);
        setCsvFile(null);
        setStatusMessage(`[DEMO] Imported CSV file: 25 new leads loaded with deduplication.`);
      }, 1200);
      return;
    }

    setImportingCsv(true);
    try {
      const formData = new FormData();
      formData.append("file", csvFile);
      if (importSelectedPurpose) {
        formData.append("purpose_id", importSelectedPurpose);
      }
      formData.append("auto_batch", "true");

      const res = await fetch(`${apiUrl}/api/v1/contacts/import-csv`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setStatusMessage(`CSV imported: ${data.created_count} contacts added, ${data.duplicate_count} duplicates skipped.`);
        setCsvFile(null);
        loadAllData();
      } else {
        const err = await res.json();
        setStatusMessage(`CSV Import Error: ${err.detail}`);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setImportingCsv(false);
    }
  };

  const handleMatchJd = async () => {
    if (!jdText.trim()) return;

    if (isDemoMode) {
      setJdMatching(true);
      setTimeout(() => {
        setJdMatching(false);
        setJdMatchResult({
          match_score: 94,
          matched_skills: ["Python", "FastAPI", "Generative AI", "RAG Pipelines", "PostgreSQL", "Docker", "AsyncIO"],
          gap_skills: ["Kubernetes Cluster Administration"],
          personalized_pitch:
            "Hi hiring manager, I noticed your search for an engineer to architect high-concurrency Python & LLM workflows. In my recent work building MailOrbit (PostgreSQL, Gemini BYOK, Google Apps Script zero-password relay) and the ABCD Smart Campus (386k+ LOC), I delivered sub-100ms response latencies and zero-leak cryptographic pipelines.",
          suggested_subject: "Python / GenAI Engineer for your High-Concurrency Team",
        });
      }, 1000);
      return;
    }

    setJdMatching(true);
    try {
      const res = await apiFetch("/api/v1/profile/match-jd", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_description: jdText }),
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

    if (isDemoMode) {
      setKeySaving(true);
      setTimeout(() => {
        setKeySaving(false);
        setNewGeminiKey("");
        setStatusMessage("[DEMO] Gemini BYOK Key securely stored and tested against Gemini 2.5 Flash!");
      }, 800);
      return;
    }

    setKeySaving(true);
    try {
      const res = await apiFetch("/api/v1/ai-keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: "gemini",
          api_key: newGeminiKey.trim(),
          preferred_model: keyModel,
        }),
      });
      if (res.ok) {
        setNewGeminiKey("");
        loadAllData();
        setStatusMessage("Gemini API key encrypted and saved successfully!");
      }
    } catch (err) {
      console.error(err);
    } finally {
      setKeySaving(false);
    }
  };

  const handleSaveRelay = async () => {
    if (!relayScriptUrl.trim()) return;

    if (isDemoMode) {
      setRelaySaving(true);
      setTimeout(() => {
        setRelaySaving(false);
        setStatusMessage("[DEMO] Google Apps Script relay connected over HTTPS:443 with 10% safety pause!");
      }, 800);
      return;
    }

    setRelaySaving(true);
    try {
      const res = await apiFetch("/api/v1/senders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider_type: "google_apps_script",
          sender_email: relayEmail || "user@gmail.com",
          relay_url: relayScriptUrl.trim(),
          relay_auth_token: relayAuthToken.trim(),
          daily_limit: 50,
        }),
      });
      if (res.ok) {
        setRelayScriptUrl("");
        setRelayAuthToken("");
        loadAllData();
        setStatusMessage("Google Apps Script relay saved and verified!");
      }
    } catch (err) {
      console.error(err);
    } finally {
      setRelaySaving(false);
    }
  };

  const filteredContacts = contacts.filter((c) => {
    const matchesSearch =
      contactSearch === "" ||
      c.name?.toLowerCase().includes(contactSearch.toLowerCase()) ||
      c.email?.toLowerCase().includes(contactSearch.toLowerCase()) ||
      c.company?.toLowerCase().includes(contactSearch.toLowerCase());
    const matchesFilter = contactFilter === "ALL" || c.status === contactFilter;
    return matchesSearch && matchesFilter;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh", background: "#0b0f19", color: "#f8fafc", fontFamily: "system-ui, -apple-system, sans-serif" }}>
      {/* Top Universal Brand Header */}
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "12px 28px",
          background: "#0f172a",
          borderBottom: "1px solid #1e293b",
          position: "sticky",
          top: 0,
          zIndex: 40,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
          <OrbitalLogo size={38} />
          {/* Quick status pill */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "4px 10px",
              borderRadius: "20px",
              background: isDemoMode ? "rgba(245, 158, 11, 0.12)" : apiHealthy ? "rgba(34, 197, 94, 0.12)" : "rgba(56, 189, 248, 0.1)",
              border: `1px solid ${isDemoMode ? "#f59e0b" : apiHealthy ? "#22c55e" : "#38bdf8"}`,
              fontSize: "0.75rem",
              fontWeight: 600,
              color: isDemoMode ? "#fbbf24" : apiHealthy ? "#4ade80" : "#38bdf8",
            }}
          >
            <span
              style={{
                width: "7px",
                height: "7px",
                borderRadius: "50%",
                background: isDemoMode ? "#f59e0b" : apiHealthy ? "#22c55e" : "#38bdf8",
                boxShadow: isDemoMode ? "0 0 8px #f59e0b" : apiHealthy ? "0 0 8px #22c55e" : "0 0 8px #38bdf8",
              }}
            />
            {isDemoMode ? "Interactive Sandbox / Demo" : apiHealthy ? "Cloud System Online" : "Connecting..."}
          </div>
        </div>

        {/* Right Header Navigation & User Actions */}
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <button
            onClick={() => setActiveTab("about")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              background: activeTab === "about" ? "#1e293b" : "transparent",
              color: activeTab === "about" ? "#38bdf8" : "#94a3b8",
              border: "1px solid",
              borderColor: activeTab === "about" ? "#0284c7" : "#334155",
              padding: "6px 14px",
              borderRadius: "6px",
              fontSize: "0.82rem",
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            <Code2 size={14} color="#38bdf8" />
            Creator & Portfolio
          </button>

          {!token && !isDemoMode ? (
            <button
              onClick={enableDemoMode}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                background: "linear-gradient(135deg, #0284c7 0%, #4f46e5 100%)",
                color: "#ffffff",
                border: "none",
                padding: "7px 16px",
                borderRadius: "6px",
                fontSize: "0.82rem",
                fontWeight: 600,
                cursor: "pointer",
                boxShadow: "0 2px 10px rgba(2, 132, 199, 0.35)",
              }}
            >
              <Zap size={14} />
              Try Demo / Sandbox
            </button>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "5px 12px",
                  background: "#1e293b",
                  borderRadius: "6px",
                  fontSize: "0.82rem",
                  border: "1px solid #334155",
                }}
              >
                {currentUser?.is_superuser && <Crown size={14} color="#fbbf24" />}
                <span style={{ color: "#e2e8f0" }}>{currentUser?.email || "User"}</span>
                {currentUser?.is_superuser && (
                  <span style={{ fontSize: "0.68rem", background: "#f59e0b", color: "#000000", fontWeight: 700, padding: "1px 5px", borderRadius: "4px" }}>
                    SUPERUSER
                  </span>
                )}
              </div>

              {isDemoMode ? (
                <button
                  onClick={exitDemoMode}
                  style={{
                    background: "#b45309",
                    color: "#ffffff",
                    border: "none",
                    padding: "6px 12px",
                    borderRadius: "6px",
                    fontSize: "0.8rem",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Exit Demo
                </button>
              ) : (
                <button
                  onClick={handleLogout}
                  title="Sign Out"
                  style={{
                    background: "transparent",
                    color: "#94a3b8",
                    border: "1px solid #334155",
                    padding: "6px 10px",
                    borderRadius: "6px",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                  }}
                >
                  <LogOut size={14} />
                </button>
              )}
            </div>
          )}
        </div>
      </header>

      {/* Demo Sandbox Alert Banner */}
      {isDemoMode && (
        <div
          style={{
            background: "linear-gradient(90deg, #78350f 0%, #451a03 100%)",
            borderBottom: "1px solid #b45309",
            padding: "8px 28px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: "0.82rem",
            color: "#fef3c7",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Zap size={14} color="#fbbf24" />
            <span>
              <strong>[DEMO / SANDBOX MODE]</strong> You are exploring MailOrbit in an interactive simulated environment. Zero server bypass, safe client-side sandbox.
            </span>
          </div>
          <button
            onClick={exitDemoMode}
            style={{
              background: "#d97706",
              color: "#ffffff",
              border: "none",
              padding: "3px 10px",
              borderRadius: "4px",
              fontSize: "0.75rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Switch to Live Cloud
          </button>
        </div>
      )}

      {/* Main Layout Container */}
      <div style={{ display: "flex", flex: 1 }}>
        {/* Left Sidebar Navigation */}
        <aside
          style={{
            width: "240px",
            background: "#0d1322",
            borderRight: "1px solid #1e293b",
            padding: "20px 14px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}
        >
          <div>
            <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "#64748b", letterSpacing: "0.06em", padding: "0 10px 12px" }}>
              PLATFORM WORKSPACE
            </div>

            <nav style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <button
                onClick={() => setActiveTab("overview")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "9px 12px",
                  borderRadius: "6px",
                  background: activeTab === "overview" ? "#1e293b" : "transparent",
                  color: activeTab === "overview" ? "#38bdf8" : "#94a3b8",
                  border: "none",
                  textAlign: "left",
                  fontSize: "0.88rem",
                  fontWeight: activeTab === "overview" ? 600 : 500,
                  cursor: "pointer",
                }}
              >
                <Activity size={16} />
                Overview
              </button>

              <button
                onClick={() => setActiveTab("campaigns")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "9px 12px",
                  borderRadius: "6px",
                  background: activeTab === "campaigns" ? "#1e293b" : "transparent",
                  color: activeTab === "campaigns" ? "#38bdf8" : "#94a3b8",
                  border: "none",
                  textAlign: "left",
                  fontSize: "0.88rem",
                  fontWeight: activeTab === "campaigns" ? 600 : 500,
                  cursor: "pointer",
                }}
              >
                <Layers size={16} />
                Campaigns & Batches
              </button>

              <button
                onClick={() => setActiveTab("contacts")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "9px 12px",
                  borderRadius: "6px",
                  background: activeTab === "contacts" ? "#1e293b" : "transparent",
                  color: activeTab === "contacts" ? "#38bdf8" : "#94a3b8",
                  border: "none",
                  textAlign: "left",
                  fontSize: "0.88rem",
                  fontWeight: activeTab === "contacts" ? 600 : 500,
                  cursor: "pointer",
                }}
              >
                <Mail size={16} />
                Leads & CSV Import
              </button>

              <button
                onClick={() => setActiveTab("ai")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "9px 12px",
                  borderRadius: "6px",
                  background: activeTab === "ai" ? "#1e293b" : "transparent",
                  color: activeTab === "ai" ? "#38bdf8" : "#94a3b8",
                  border: "none",
                  textAlign: "left",
                  fontSize: "0.88rem",
                  fontWeight: activeTab === "ai" ? 600 : 500,
                  cursor: "pointer",
                }}
              >
                <Sparkles size={16} />
                AI Personalizer & JD
              </button>

              <button
                onClick={() => setActiveTab("settings")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "9px 12px",
                  borderRadius: "6px",
                  background: activeTab === "settings" ? "#1e293b" : "transparent",
                  color: activeTab === "settings" ? "#38bdf8" : "#94a3b8",
                  border: "none",
                  textAlign: "left",
                  fontSize: "0.88rem",
                  fontWeight: activeTab === "settings" ? 600 : 500,
                  cursor: "pointer",
                }}
              >
                <Key size={16} />
                Sender Relay & Keys
              </button>

              <div style={{ height: "1px", background: "#1e293b", margin: "14px 0 10px" }} />

              <button
                onClick={() => setActiveTab("about")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "9px 12px",
                  borderRadius: "6px",
                  background: activeTab === "about" ? "#1e293b" : "transparent",
                  color: activeTab === "about" ? "#38bdf8" : "#94a3b8",
                  border: "none",
                  textAlign: "left",
                  fontSize: "0.88rem",
                  fontWeight: activeTab === "about" ? 600 : 500,
                  cursor: "pointer",
                }}
              >
                <User size={16} />
                About Vikas Dangi
              </button>

              {(currentUser?.is_superuser || isDemoMode) && (
                <button
                  onClick={() => setActiveTab("admin")}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    padding: "9px 12px",
                    borderRadius: "6px",
                    background: activeTab === "admin" ? "rgba(245, 158, 11, 0.15)" : "transparent",
                    color: activeTab === "admin" ? "#fbbf24" : "#e2e8f0",
                    border: activeTab === "admin" ? "1px solid #f59e0b" : "1px solid transparent",
                    textAlign: "left",
                    fontSize: "0.88rem",
                    fontWeight: 600,
                    cursor: "pointer",
                    marginTop: "4px",
                  }}
                >
                  <Crown size={16} color="#fbbf24" />
                  Admin Control Deck
                </button>
              )}
            </nav>
          </div>

          {/* Quick Footer Links */}
          <div style={{ padding: "10px", background: "#0b101d", borderRadius: "8px", border: "1px solid #1e293b" }}>
            <div style={{ fontSize: "0.72rem", color: "#64748b", marginBottom: "6px" }}>BUILT BY</div>
            <div style={{ fontWeight: 600, fontSize: "0.84rem", color: "#e2e8f0" }}>Vikas Dangi</div>
            <div style={{ fontSize: "0.72rem", color: "#38bdf8" }}>Generative AI & Full-Stack</div>
            <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
              <a href="https://github.com/Vikas003dangi" target="_blank" rel="noreferrer" style={{ color: "#94a3b8" }}>
                <Github size={14} />
              </a>
              <a href="https://linkedin.com/in/vikas-dangi-dev" target="_blank" rel="noreferrer" style={{ color: "#94a3b8" }}>
                <Linkedin size={14} />
              </a>
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <main style={{ flex: 1, padding: "32px 36px", overflowY: "auto", maxWidth: "1280px" }}>
          {/* Status Message Notification */}
          {statusMessage && (
            <div
              style={{
                marginBottom: "24px",
                padding: "12px 18px",
                borderRadius: "8px",
                background: "#0c4a6e",
                border: "1px solid #0284c7",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                color: "#e0f2fe",
                fontSize: "0.88rem",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <CheckCircle2 size={16} color="#38bdf8" />
                <span>{statusMessage}</span>
              </div>
              <button
                onClick={() => setStatusMessage(null)}
                style={{ background: "transparent", border: "none", color: "#93c5fd", cursor: "pointer", fontSize: "0.85rem" }}
              >
                Dismiss
              </button>
            </div>
          )}

          {/* If Not Logged In and not in Demo Mode (and not viewing About tab), Display Auth Card */}
          {!token && !isDemoMode && activeTab !== "about" ? (
            <div style={{ maxWidth: "440px", margin: "40px auto", background: "#111827", padding: "36px", borderRadius: "14px", border: "1px solid #1f2937", boxShadow: "0 10px 30px rgba(0,0,0,0.5)" }}>
              <div style={{ textAlign: "center", marginBottom: "26px" }}>
                <div style={{ display: "flex", justifyContent: "center", marginBottom: "12px" }}>
                  <OrbitalLogo size={48} />
                </div>
                <h2 style={{ fontSize: "1.45rem", fontWeight: 700, margin: "8px 0 4px" }}>
                  {authMode === "login" ? "Welcome Back to MailOrbit" : "Create Your Free Workspace"}
                </h2>
                <p style={{ color: "#94a3b8", fontSize: "0.85rem", margin: 0 }}>
                  Autonomous cold-email engine with smart batch pacing & BYOK AI.
                </p>
              </div>

              {/* Login / Sign Up Tabs */}
              <div style={{ display: "flex", borderBottom: "1px solid #1f2937", marginBottom: "20px" }}>
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode("login");
                    setAuthError(null);
                    setAuthStatusText(null);
                  }}
                  style={{
                    flex: 1,
                    padding: "10px",
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
                  type="button"
                  onClick={() => {
                    setAuthMode("signup");
                    setAuthError(null);
                    setAuthStatusText(null);
                  }}
                  style={{
                    flex: 1,
                    padding: "10px",
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

              {/* Honest Wake-up / Retry Status Alert */}
              {authStatusText && (
                <div
                  style={{
                    background: "rgba(56, 189, 248, 0.12)",
                    border: "1px solid #0284c7",
                    color: "#7dd3fc",
                    padding: "12px 14px",
                    borderRadius: "8px",
                    marginBottom: "16px",
                    fontSize: "0.84rem",
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                  }}
                >
                  <RefreshCw size={16} className="animate-spin" color="#38bdf8" />
                  <span>{authStatusText}</span>
                </div>
              )}

              {/* Error Alert Box */}
              {authError && (
                <div
                  style={{
                    background: "rgba(239, 68, 68, 0.15)",
                    border: "1px solid #ef4444",
                    color: "#fca5a5",
                    padding: "12px 14px",
                    borderRadius: "8px",
                    marginBottom: "16px",
                    fontSize: "0.84rem",
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "8px",
                  }}
                >
                  <AlertCircle size={16} color="#ef4444" style={{ flexShrink: 0, marginTop: "2px" }} />
                  <div>{authError}</div>
                </div>
              )}

              {/* Auth Form */}
              <form onSubmit={handleAuth} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.82rem", color: "#9ca3af", marginBottom: "6px" }}>
                    Email Address
                  </label>
                  <input
                    type="email"
                    required
                    value={authEmail}
                    onChange={(e) => setAuthEmail(e.target.value)}
                    placeholder="you@company.com"
                    style={{
                      width: "100%",
                      padding: "11px 14px",
                      borderRadius: "8px",
                      background: "#1f2937",
                      border: "1px solid #374151",
                      color: "#ffffff",
                      fontSize: "0.9rem",
                      boxSizing: "border-box",
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.82rem", color: "#9ca3af", marginBottom: "6px" }}>
                    Password
                  </label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={authPassword}
                    onChange={(e) => setAuthPassword(e.target.value)}
                    placeholder="••••••••••••"
                    style={{
                      width: "100%",
                      padding: "11px 14px",
                      borderRadius: "8px",
                      background: "#1f2937",
                      border: "1px solid #374151",
                      color: "#ffffff",
                      fontSize: "0.9rem",
                      boxSizing: "border-box",
                    }}
                  />
                </div>

                <button
                  type="submit"
                  disabled={authLoading}
                  style={{
                    background: authLoading ? "#0369a1" : "linear-gradient(135deg, #0284c7 0%, #2563eb 100%)",
                    color: "#ffffff",
                    border: "none",
                    padding: "12px",
                    borderRadius: "8px",
                    fontWeight: 600,
                    fontSize: "0.95rem",
                    cursor: authLoading ? "not-allowed" : "pointer",
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    gap: "8px",
                    marginTop: "8px",
                  }}
                >
                  {authLoading && <RefreshCw size={16} className="animate-spin" />}
                  {authLoading ? "Connecting..." : authMode === "login" ? "Sign In to Workspace" : "Create Workspace"}
                </button>
              </form>

              {/* Instant Sandbox Button */}
              <div style={{ marginTop: "24px", paddingTop: "20px", borderTop: "1px solid #1f2937", textAlign: "center" }}>
                <p style={{ fontSize: "0.82rem", color: "#94a3b8", marginBottom: "12px" }}>
                  Want to explore without creating an account?
                </p>
                <button
                  onClick={enableDemoMode}
                  style={{
                    width: "100%",
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    gap: "8px",
                    background: "#1e293b",
                    color: "#38bdf8",
                    border: "1px solid #0284c7",
                    padding: "10px",
                    borderRadius: "8px",
                    fontWeight: 600,
                    fontSize: "0.85rem",
                    cursor: "pointer",
                  }}
                >
                  <Zap size={14} color="#38bdf8" />
                  ⚡ Launch Interactive Sandbox (Demo Mode)
                </button>
              </div>
            </div>
          ) : (
            /* Authenticated or Demo Dashboard View */
            <div>
              {/* Overview Tab */}
              {activeTab === "overview" && (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "28px" }}>
                    <div>
                      <h1 style={{ fontSize: "1.85rem", fontWeight: 700, margin: "0 0 6px" }}>Outreach Command Center</h1>
                      <p style={{ color: "#94a3b8", fontSize: "0.92rem", margin: 0 }}>
                        Autonomous cold outreach orchestrator: pacing 30 emails/day with automatic bounce replacement.
                      </p>
                    </div>
                    <div style={{ display: "flex", gap: "10px" }}>
                      <button
                        onClick={() => setActiveTab("campaigns")}
                        style={{
                          background: "#0284c7",
                          color: "#ffffff",
                          border: "none",
                          padding: "9px 16px",
                          borderRadius: "6px",
                          fontWeight: 600,
                          fontSize: "0.85rem",
                          cursor: "pointer",
                        }}
                      >
                        + Create Purpose
                      </button>
                    </div>
                  </div>

                  {/* High Level Metrics Cards */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "32px" }}>
                    <div style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937" }}>
                      <div style={{ fontSize: "0.8rem", color: "#94a3b8", fontWeight: 500, marginBottom: "8px" }}>TOTAL LEADS</div>
                      <div style={{ fontSize: "1.8rem", fontWeight: 700, color: "#ffffff" }}>
                        {contacts.length > 0 ? contacts.length : 360}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "#22c55e", marginTop: "4px" }}>Deduplicated & verified</div>
                    </div>

                    <div style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937" }}>
                      <div style={{ fontSize: "0.8rem", color: "#94a3b8", fontWeight: 500, marginBottom: "8px" }}>ACTIVE BATCHES</div>
                      <div style={{ fontSize: "1.8rem", fontWeight: 700, color: "#38bdf8" }}>
                        {batches.filter((b) => b.status === "ACTIVE" || b.status === "SCHEDULED").length}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "4px" }}>Pacing 30 emails / day</div>
                    </div>

                    <div style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937" }}>
                      <div style={{ fontSize: "0.8rem", color: "#94a3b8", fontWeight: 500, marginBottom: "8px" }}>DELIVERY ENGINE</div>
                      <div style={{ fontSize: "1.8rem", fontWeight: 700, color: "#22c55e" }}>
                        {relays.length > 0 || isDemoMode ? "ONLINE" : "STANDBY"}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "4px" }}>Google Apps Script HTTPS:443</div>
                    </div>

                    <div style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937" }}>
                      <div style={{ fontSize: "0.8rem", color: "#94a3b8", fontWeight: 500, marginBottom: "8px" }}>AI PERSONALIZER</div>
                      <div style={{ fontSize: "1.8rem", fontWeight: 700, color: "#c084fc" }}>
                        {aiKeys.length > 0 || isDemoMode ? "BYOK ACTIVE" : "READY"}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "4px" }}>Gemini 2.5 Flash Tailoring</div>
                    </div>
                  </div>

                  {/* Daily Pacing Timeline */}
                  <div style={{ background: "#111827", padding: "24px", borderRadius: "12px", border: "1px solid #1f2937", marginBottom: "32px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px" }}>
                      <div>
                        <h3 style={{ margin: "0 0 4px", fontSize: "1.1rem" }}>Scheduled Batch Pacing Schedule</h3>
                        <p style={{ color: "#94a3b8", fontSize: "0.85rem", margin: 0 }}>
                          Strict daily rate limiting protects your domain reputation. If any email bounces, the replacement queue steps in.
                        </p>
                      </div>
                      <span style={{ fontSize: "0.8rem", color: "#38bdf8", background: "rgba(56, 189, 248, 0.1)", padding: "4px 10px", borderRadius: "6px" }}>
                        Safety Circuit Breaker: 10%
                      </span>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "14px" }}>
                      {batches.slice(0, 4).map((b) => (
                        <div
                          key={b.id}
                          style={{
                            background: "#1f2937",
                            padding: "16px",
                            borderRadius: "8px",
                            borderLeft: `4px solid ${b.status === "COMPLETED" ? "#22c55e" : b.status === "ACTIVE" ? "#38bdf8" : "#f59e0b"}`,
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                            <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>Batch #{b.batch_number}</span>
                            <span
                              style={{
                                fontSize: "0.72rem",
                                fontWeight: 700,
                                padding: "2px 8px",
                                borderRadius: "4px",
                                background: b.status === "COMPLETED" ? "#166534" : b.status === "ACTIVE" ? "#075985" : "#78350f",
                                color: "#ffffff",
                              }}
                            >
                              {b.status}
                            </span>
                          </div>
                          <div style={{ fontSize: "0.82rem", color: "#9ca3af", marginBottom: "10px" }}>
                            Time: {b.scheduled_time || "09:30 AM"} | Contacts: {b.total_contacts || 30}
                          </div>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <span style={{ fontSize: "0.78rem", color: "#e2e8f0" }}>
                              Sent: {b.sent_count || 0} / {b.total_contacts || 30}
                            </span>
                            {b.status !== "COMPLETED" && (
                              <button
                                onClick={() => handleDispatchBatch(b.id)}
                                style={{
                                  background: "#0284c7",
                                  color: "#ffffff",
                                  border: "none",
                                  padding: "5px 12px",
                                  borderRadius: "4px",
                                  fontSize: "0.75rem",
                                  fontWeight: 600,
                                  cursor: "pointer",
                                }}
                              >
                                Dispatch Now
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Campaigns & Batches Tab */}
              {activeTab === "campaigns" && (
                <div>
                  <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 6px" }}>Campaign Purposes & Batches</h1>
                  <p style={{ color: "#94a3b8", fontSize: "0.92rem", margin: "0 0 24px" }}>
                    Configure target purposes and auto-slice contacts into timezone-aware daily batches.
                  </p>

                  {/* Create Purpose Section */}
                  <div style={{ background: "#111827", padding: "22px", borderRadius: "10px", border: "1px solid #1f2937", marginBottom: "28px" }}>
                    <h3 style={{ margin: "0 0 16px", fontSize: "1.1rem" }}>Create New Campaign Purpose</h3>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "14px" }}>
                      <div>
                        <label style={{ display: "block", fontSize: "0.82rem", color: "#9ca3af", marginBottom: "4px" }}>Purpose Name</label>
                        <input
                          type="text"
                          value={newPurposeName}
                          onChange={(e) => setNewPurposeName(e.target.value)}
                          placeholder="e.g. Senior Backend Job Application"
                          style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box" }}
                        />
                      </div>
                      <div>
                        <label style={{ display: "block", fontSize: "0.82rem", color: "#9ca3af", marginBottom: "4px" }}>Subject Template</label>
                        <input
                          type="text"
                          value={newPurposeSubject}
                          onChange={(e) => setNewPurposeSubject(e.target.value)}
                          style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box" }}
                        />
                      </div>
                    </div>
                    <div style={{ marginBottom: "14px" }}>
                      <label style={{ display: "block", fontSize: "0.82rem", color: "#9ca3af", marginBottom: "4px" }}>Body Template</label>
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

                  {/* Purposes Grid */}
                  <div style={{ marginBottom: "32px" }}>
                    <h3 style={{ margin: "0 0 16px", fontSize: "1.1rem" }}>Active Purposes</h3>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "16px" }}>
                      {purposes.map((p) => (
                        <div key={p.id} style={{ background: "#111827", padding: "18px", borderRadius: "8px", border: "1px solid #1f2937" }}>
                          <div style={{ fontWeight: 600, fontSize: "1.05rem", color: "#38bdf8", marginBottom: "6px" }}>{p.name}</div>
                          <div style={{ fontSize: "0.82rem", color: "#9ca3af", marginBottom: "14px" }}>
                            Subject: {p.default_subject_template}
                          </div>
                          <button
                            onClick={() => handleAutoBatch(p.id)}
                            style={{ background: "#1e293b", color: "#38bdf8", border: "1px solid #0284c7", padding: "6px 12px", borderRadius: "6px", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600 }}
                          >
                            Auto-Slice Batches (30/day)
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
                  <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 6px" }}>Leads & CSV Import</h1>
                  <p style={{ color: "#94a3b8", fontSize: "0.92rem", margin: "0 0 24px" }}>
                    Upload contacts CSV with automated column normalization, deduplication, and replacement fallback.
                  </p>

                  {/* Upload Box */}
                  <form onSubmit={handleUploadCsv} style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937", marginBottom: "28px" }}>
                    <h3 style={{ margin: "0 0 14px", fontSize: "1.05rem" }}>Upload Leads CSV</h3>
                    <div style={{ display: "flex", gap: "16px", alignItems: "center", marginBottom: "14px" }}>
                      <input
                        type="file"
                        accept=".csv"
                        onChange={(e) => setCsvFile(e.target.files ? e.target.files[0] : null)}
                        style={{ padding: "8px", background: "#1f2937", borderRadius: "6px", border: "1px solid #374151", color: "#9ca3af", flex: 1 }}
                      />
                      <button
                        type="submit"
                        disabled={!csvFile || importingCsv}
                        style={{
                          background: importingCsv ? "#0369a1" : "#0284c7",
                          color: "#ffffff",
                          border: "none",
                          padding: "10px 20px",
                          borderRadius: "6px",
                          cursor: importingCsv || !csvFile ? "not-allowed" : "pointer",
                          fontWeight: 600,
                        }}
                      >
                        {importingCsv ? "Importing..." : "Process CSV"}
                      </button>
                    </div>
                  </form>

                  {/* Leads Filter & Search Table */}
                  <div style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                      <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                        <Search size={16} color="#94a3b8" />
                        <input
                          type="text"
                          value={contactSearch}
                          onChange={(e) => setContactSearch(e.target.value)}
                          placeholder="Search name, company, email..."
                          style={{ padding: "6px 12px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", fontSize: "0.85rem" }}
                        />
                      </div>
                      <div style={{ display: "flex", gap: "6px" }}>
                        {["ALL", "PENDING", "QUEUED", "SENT", "REPLACED"].map((st) => (
                          <button
                            key={st}
                            onClick={() => setContactFilter(st)}
                            style={{
                              padding: "4px 10px",
                              borderRadius: "4px",
                              fontSize: "0.75rem",
                              fontWeight: 600,
                              background: contactFilter === st ? "#0284c7" : "#1f2937",
                              color: contactFilter === st ? "#ffffff" : "#94a3b8",
                              border: "none",
                              cursor: "pointer",
                            }}
                          >
                            {st}
                          </button>
                        ))}
                      </div>
                    </div>

                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
                      <thead>
                        <tr style={{ borderBottom: "1px solid #1f2937", color: "#9ca3af", textAlign: "left" }}>
                          <th style={{ padding: "10px" }}>Name</th>
                          <th style={{ padding: "10px" }}>Email</th>
                          <th style={{ padding: "10px" }}>Company</th>
                          <th style={{ padding: "10px" }}>Role</th>
                          <th style={{ padding: "10px" }}>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredContacts.map((c) => (
                          <tr key={c.id} style={{ borderBottom: "1px solid #1f2937" }}>
                            <td style={{ padding: "10px", fontWeight: 600 }}>{c.name}</td>
                            <td style={{ padding: "10px", color: "#94a3b8" }}>{c.email}</td>
                            <td style={{ padding: "10px" }}>{c.company}</td>
                            <td style={{ padding: "10px", color: "#94a3b8" }}>{c.role || "Recruiter"}</td>
                            <td style={{ padding: "10px" }}>
                              <span
                                style={{
                                  padding: "2px 8px",
                                  borderRadius: "4px",
                                  fontSize: "0.72rem",
                                  fontWeight: 700,
                                  background:
                                    c.status === "SENT"
                                      ? "#166534"
                                      : c.status === "QUEUED"
                                      ? "#075985"
                                      : c.status === "REPLACED"
                                      ? "#581c87"
                                      : "#374151",
                                  color: "#ffffff",
                                }}
                              >
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

              {/* AI Personalizer & JD Matcher Tab */}
              {activeTab === "ai" && (
                <div>
                  <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 6px" }}>AI Personalizer & JD Matcher</h1>
                  <p style={{ color: "#94a3b8", fontSize: "0.92rem", margin: "0 0 24px" }}>
                    Bring Your Own Gemini API Key (BYOK) to scan resumes, extract skills, and generate tailored cold-email icebreakers.
                  </p>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", marginBottom: "32px" }}>
                    {/* Gemini Key Config */}
                    <div style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937" }}>
                      <h3 style={{ margin: "0 0 12px", fontSize: "1.05rem" }}>Configure Gemini Key (BYOK)</h3>
                      <div style={{ marginBottom: "12px" }}>
                        <label style={{ display: "block", fontSize: "0.82rem", color: "#9ca3af", marginBottom: "4px" }}>
                          Gemini API Key
                        </label>
                        <input
                          type="password"
                          value={newGeminiKey}
                          onChange={(e) => setNewGeminiKey(e.target.value)}
                          placeholder="AIzaSy..."
                          style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box" }}
                        />
                      </div>
                      <div style={{ marginBottom: "16px" }}>
                        <label style={{ display: "block", fontSize: "0.82rem", color: "#9ca3af", marginBottom: "4px" }}>
                          Target Model
                        </label>
                        <select
                          value={keyModel}
                          onChange={(e) => setKeyModel(e.target.value)}
                          style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box" }}
                        >
                          <option value="gemini-2.5-flash">Gemini 2.5 Flash (Recommended - Fastest)</option>
                          <option value="gemini-1.5-pro">Gemini 1.5 Pro (Deep Tailoring)</option>
                        </select>
                      </div>
                      <button
                        onClick={handleSaveGeminiKey}
                        disabled={keySaving}
                        style={{ background: "#0284c7", color: "#ffffff", border: "none", padding: "10px 18px", borderRadius: "6px", cursor: "pointer", fontWeight: 600 }}
                      >
                        {keySaving ? "Validating & Encrypting..." : "Save Encrypted Key"}
                      </button>
                    </div>

                    {/* Resume Matcher */}
                    <div style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937" }}>
                      <h3 style={{ margin: "0 0 12px", fontSize: "1.05rem" }}>Match Candidate Profile against JD</h3>
                      <div style={{ marginBottom: "12px" }}>
                        <label style={{ display: "block", fontSize: "0.82rem", color: "#9ca3af", marginBottom: "4px" }}>
                          Paste Target Job Description (JD)
                        </label>
                        <textarea
                          rows={4}
                          value={jdText}
                          onChange={(e) => setJdText(e.target.value)}
                          placeholder="We are looking for a Senior Python & GenAI Engineer experienced in RAG..."
                          style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box", fontFamily: "inherit" }}
                        />
                      </div>
                      <button
                        onClick={handleMatchJd}
                        disabled={jdMatching || !jdText.trim()}
                        style={{ background: "#7c3aed", color: "#ffffff", border: "none", padding: "10px 18px", borderRadius: "6px", cursor: "pointer", fontWeight: 600 }}
                      >
                        {jdMatching ? "Analyzing Fit..." : "Generate Custom Pitch"}
                      </button>
                    </div>
                  </div>

                  {/* AI Results */}
                  {jdMatchResult && (
                    <div style={{ background: "#111827", padding: "24px", borderRadius: "10px", border: "1px solid #7c3aed" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                        <h3 style={{ margin: 0, fontSize: "1.1rem" }}>Tailored Match Analysis</h3>
                        <span style={{ fontSize: "1rem", fontWeight: 700, color: "#a855f7" }}>
                          Match Score: {jdMatchResult.match_score}%
                        </span>
                      </div>
                      <div style={{ marginBottom: "14px" }}>
                        <div style={{ fontSize: "0.82rem", color: "#9ca3af", marginBottom: "4px" }}>Suggested Subject Line:</div>
                        <div style={{ fontWeight: 600, color: "#38bdf8" }}>{jdMatchResult.suggested_subject}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: "0.82rem", color: "#9ca3af", marginBottom: "4px" }}>Personalized Email Pitch:</div>
                        <div style={{ background: "#1f2937", padding: "14px", borderRadius: "6px", fontSize: "0.88rem", whiteSpace: "pre-wrap", color: "#e2e8f0" }}>
                          {jdMatchResult.personalized_pitch}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Sender Relay & Keys Tab */}
              {activeTab === "settings" && (
                <div>
                  <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 6px" }}>Sender Relay & Keys</h1>
                  <p style={{ color: "#94a3b8", fontSize: "0.92rem", margin: "0 0 24px" }}>
                    Configure your zero-password Google Apps Script egress relay over HTTPS:443 with safety circuit breaker.
                  </p>

                  <div style={{ maxWidth: "600px", background: "#111827", padding: "24px", borderRadius: "10px", border: "1px solid #1f2937" }}>
                    <h3 style={{ margin: "0 0 16px", fontSize: "1.1rem" }}>Google Apps Script Web App Relay</h3>
                    <div style={{ marginBottom: "14px" }}>
                      <label style={{ display: "block", fontSize: "0.82rem", color: "#9ca3af", marginBottom: "4px" }}>
                        Sender Gmail Address
                      </label>
                      <input
                        type="email"
                        value={relayEmail}
                        onChange={(e) => setRelayEmail(e.target.value)}
                        placeholder="you@gmail.com"
                        style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box" }}
                      />
                    </div>
                    <div style={{ marginBottom: "14px" }}>
                      <label style={{ display: "block", fontSize: "0.82rem", color: "#9ca3af", marginBottom: "4px" }}>
                        Apps Script Web App URL
                      </label>
                      <input
                        type="url"
                        value={relayScriptUrl}
                        onChange={(e) => setRelayScriptUrl(e.target.value)}
                        placeholder="https://script.google.com/macros/s/.../exec"
                        style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box" }}
                      />
                    </div>
                    <div style={{ marginBottom: "18px" }}>
                      <label style={{ display: "block", fontSize: "0.82rem", color: "#9ca3af", marginBottom: "4px" }}>
                        Relay Secret Token
                      </label>
                      <input
                        type="password"
                        value={relayAuthToken}
                        onChange={(e) => setRelayAuthToken(e.target.value)}
                        placeholder="Secret defined in Apps Script properties"
                        style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box" }}
                      />
                    </div>
                    <button
                      onClick={handleSaveRelay}
                      disabled={relaySaving}
                      style={{ background: "#0284c7", color: "#ffffff", border: "none", padding: "10px 18px", borderRadius: "6px", cursor: "pointer", fontWeight: 600 }}
                    >
                      {relaySaving ? "Saving..." : "Connect Relay"}
                    </button>
                  </div>
                </div>
              )}

              {/* Creator / About Vikas Dangi Tab */}
              {activeTab === "about" && (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px" }}>
                    <div>
                      <h1 style={{ fontSize: "1.9rem", fontWeight: 700, margin: "0 0 6px" }}>About the Creator</h1>
                      <p style={{ color: "#94a3b8", fontSize: "0.92rem", margin: 0 }}>
                        System Architect & Full-Stack Engineer behind MailOrbit and enterprise production platforms.
                      </p>
                    </div>
                    <div style={{ display: "flex", gap: "10px" }}>
                      <a
                        href="https://github.com/Vikas003dangi"
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                          background: "#1f2937",
                          color: "#ffffff",
                          textDecoration: "none",
                          padding: "8px 14px",
                          borderRadius: "6px",
                          fontSize: "0.82rem",
                          fontWeight: 600,
                          border: "1px solid #374151",
                        }}
                      >
                        <Github size={15} />
                        GitHub Profile
                      </a>
                      <a
                        href="https://linkedin.com/in/vikas-dangi-dev"
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                          background: "#0a66c2",
                          color: "#ffffff",
                          textDecoration: "none",
                          padding: "8px 14px",
                          borderRadius: "6px",
                          fontSize: "0.82rem",
                          fontWeight: 600,
                        }}
                      >
                        <Linkedin size={15} />
                        LinkedIn
                      </a>
                    </div>
                  </div>

                  {/* Creator Profile Hero Card */}
                  <div
                    style={{
                      background: "linear-gradient(135deg, #111827 0%, #1e1b4b 100%)",
                      padding: "32px",
                      borderRadius: "14px",
                      border: "1px solid #374151",
                      boxShadow: "0 12px 30px rgba(0, 0, 0, 0.4)",
                      marginBottom: "32px",
                    }}
                  >
                    <div style={{ display: "flex", gap: "28px", alignItems: "flex-start", flexWrap: "wrap" }}>
                      <div
                        style={{
                          width: "90px",
                          height: "90px",
                          borderRadius: "50%",
                          background: "linear-gradient(135deg, #0284c7 0%, #818cf8 100%)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: "2.2rem",
                          fontWeight: 800,
                          color: "#ffffff",
                          boxShadow: "0 0 25px rgba(56, 189, 248, 0.5)",
                          flexShrink: 0,
                        }}
                      >
                        VD
                      </div>

                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "4px" }}>
                          <h2 style={{ fontSize: "1.75rem", fontWeight: 800, margin: 0, color: "#ffffff" }}>
                            Vikas Dangi
                          </h2>
                          <span
                            style={{
                              background: "rgba(34, 197, 94, 0.15)",
                              border: "1px solid #22c55e",
                              color: "#4ade80",
                              fontSize: "0.75rem",
                              fontWeight: 700,
                              padding: "2px 8px",
                              borderRadius: "12px",
                            }}
                          >
                            OPEN TO WORK
                          </span>
                        </div>

                        <div style={{ fontSize: "1.05rem", fontWeight: 600, color: "#38bdf8", marginBottom: "12px" }}>
                          Generative AI & Python Full-Stack Engineer | Oracle Certified GenAI Professional (2025)
                        </div>

                        <p style={{ color: "#cbd5e1", fontSize: "0.95rem", lineHeight: "1.6", margin: "0 0 18px" }}>
                          Hands-on research and production engineer specializing in high-throughput Python backends,
                          asynchronous worker architectures, RAG pipelines (RRF, MMR re-ranking, HNSW dense retrieval),
                          LLM integrations, and robust cloud services.
                        </p>

                        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                          <span style={{ background: "#1f2937", border: "1px solid #374151", color: "#93c5fd", padding: "4px 10px", borderRadius: "6px", fontSize: "0.8rem", fontWeight: 500 }}>
                            🎓 B.Tech AI & Data Science (SATI Vidisha)
                          </span>
                          <span style={{ background: "#1f2937", border: "1px solid #374151", color: "#fbbf24", padding: "4px 10px", borderRadius: "6px", fontSize: "0.8rem", fontWeight: 500 }}>
                            🏆 Oracle Certified GenAI Professional
                          </span>
                          <span style={{ background: "#1f2937", border: "1px solid #374151", color: "#a78bfa", padding: "4px 10px", borderRadius: "6px", fontSize: "0.8rem", fontWeight: 500 }}>
                            📍 Madhya Pradesh, India
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Flagship Production Engineering Impact */}
                  <h3 style={{ fontSize: "1.25rem", fontWeight: 700, margin: "0 0 16px" }}>Flagship Production Platforms</h3>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "32px" }}>
                    {/* ABCD Smart Campus */}
                    <div style={{ background: "#111827", padding: "24px", borderRadius: "12px", border: "1px solid #1f2937" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                        <div style={{ fontSize: "1.15rem", fontWeight: 700, color: "#38bdf8" }}>ABCD Smart Campus</div>
                        <span style={{ fontSize: "0.72rem", background: "#065f46", color: "#34d399", padding: "2px 8px", borderRadius: "4px", fontWeight: 700 }}>
                          LIVE ON GOOGLE PLAY
                        </span>
                      </div>
                      <p style={{ color: "#94a3b8", fontSize: "0.88rem", lineHeight: "1.5", margin: "0 0 14px" }}>
                        Full-scale enterprise education ERP system comprising <strong>386,000+ lines of code</strong> (Django 5.2, Daphne ASGI, WebSockets, Redis, PostgreSQL).
                        Powers real-time admissions, alumni networks, and institutional workflows across web and Android.
                      </p>
                      <div style={{ display: "flex", gap: "10px" }}>
                        <a
                          href="https://abcdcampus.in"
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: "#38bdf8", fontSize: "0.82rem", display: "flex", alignItems: "center", gap: "4px", textDecoration: "none" }}
                        >
                          Visit Live ERP <ExternalLink size={12} />
                        </a>
                        <a
                          href="https://play.google.com/store/apps/details?id=in.abcdcampus.app"
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: "#34d399", fontSize: "0.82rem", display: "flex", alignItems: "center", gap: "4px", textDecoration: "none" }}
                        >
                          Google Play App <ExternalLink size={12} />
                        </a>
                      </div>
                    </div>

                    {/* MailOrbit Autonomous Outreach */}
                    <div style={{ background: "#111827", padding: "24px", borderRadius: "12px", border: "1px solid #1f2937" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                        <div style={{ fontSize: "1.15rem", fontWeight: 700, color: "#c084fc" }}>MailOrbit Architecture</div>
                        <span style={{ fontSize: "0.72rem", background: "#4c1d95", color: "#c084fc", padding: "2px 8px", borderRadius: "4px", fontWeight: 700 }}>
                          PRODUCTION SAAS
                        </span>
                      </div>
                      <p style={{ color: "#94a3b8", fontSize: "0.88rem", lineHeight: "1.5", margin: "0 0 14px" }}>
                        High-availability cold outreach architecture featuring Neon Serverless PostgreSQL 16, Google Apps Script zero-password HTTPS relay,
                        Gemini BYOK AI tailoring, and automated 10% safety pause circuit breaker with replacement queues.
                      </p>
                      <div style={{ color: "#94a3b8", fontSize: "0.82rem" }}>
                        Built with: FastAPI, SQLAlchemy, Neon Serverless, Next.js, AES-256-GCM.
                      </div>
                    </div>
                  </div>

                  {/* Core Tech Stack Matrix */}
                  <div style={{ background: "#111827", padding: "24px", borderRadius: "12px", border: "1px solid #1f2937" }}>
                    <h3 style={{ margin: "0 0 16px", fontSize: "1.1rem" }}>Technical Expertise</h3>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
                      <div>
                        <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#38bdf8", marginBottom: "6px" }}>LANGUAGES & RUNTIMES</div>
                        <div style={{ color: "#cbd5e1", fontSize: "0.85rem", lineHeight: "1.6" }}>
                          Python (AsyncIO, FastAPI, Django), TypeScript, SQL (PostgreSQL), Bash
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#a855f7", marginBottom: "6px" }}>AI & LLM PIPELINES</div>
                        <div style={{ color: "#cbd5e1", fontSize: "0.85rem", lineHeight: "1.6" }}>
                          Gemini API, RAG Architectures, LangChain, SentenceTransformers, Vector Search
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#34d399", marginBottom: "6px" }}>INFRASTRUCTURE & DB</div>
                        <div style={{ color: "#cbd5e1", fontSize: "0.85rem", lineHeight: "1.6" }}>
                          PostgreSQL 16, Neon Serverless, Redis, Docker, Render Cloud, GitHub Actions
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Admin Control Deck (Superuser & Demo Mode) */}
              {activeTab === "admin" && (currentUser?.is_superuser || isDemoMode) && (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <Crown size={22} color="#fbbf24" />
                        <h1 style={{ fontSize: "1.85rem", fontWeight: 700, margin: 0 }}>Superuser Admin Control Deck</h1>
                      </div>
                      <p style={{ color: "#94a3b8", fontSize: "0.92rem", margin: "4px 0 0" }}>
                        Master telemetry, database pool monitor, and queue dispatcher for authorized administrators.
                      </p>
                    </div>
                    <button
                      onClick={loadAdminData}
                      disabled={loadingAdmin}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        background: "#1f2937",
                        color: "#38bdf8",
                        border: "1px solid #0284c7",
                        padding: "8px 14px",
                        borderRadius: "6px",
                        fontSize: "0.82rem",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      <RefreshCw size={14} className={loadingAdmin ? "animate-spin" : ""} />
                      Refresh Telemetry
                    </button>
                  </div>

                  {/* System Telemetry Row */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px", marginBottom: "28px" }}>
                    <div style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                        <Database size={18} color="#38bdf8" />
                        <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>Neon Serverless PostgreSQL</span>
                      </div>
                      <div style={{ fontSize: "0.84rem", color: "#9ca3af", marginBottom: "6px" }}>
                        Provider: {adminSystem?.database?.provider || "Neon Serverless (Ohio)"}
                      </div>
                      <div style={{ fontSize: "0.84rem", color: "#4ade80", fontWeight: 600 }}>
                        Status: Connected (SSL Mode Active)
                      </div>
                    </div>

                    <div style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                        <Server size={18} color="#c084fc" />
                        <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>Render Container Cluster</span>
                      </div>
                      <div style={{ fontSize: "0.84rem", color: "#9ca3af", marginBottom: "6px" }}>
                        Region: {adminSystem?.host?.region || "Oregon / US-West"}
                      </div>
                      <div style={{ fontSize: "0.84rem", color: "#c084fc", fontWeight: 600 }}>
                        Container: Python 3.12 FastAPI + Uvicorn
                      </div>
                    </div>

                    <div style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                        <Clock size={18} color="#f59e0b" />
                        <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>Watchdog Scheduler (/tick)</span>
                      </div>
                      <div style={{ fontSize: "0.84rem", color: "#9ca3af", marginBottom: "6px" }}>
                        Security: Header-Only X-Tick-Secret
                      </div>
                      <div style={{ fontSize: "0.84rem", color: "#fbbf24", fontWeight: 600 }}>
                        Standby Mode: Zero queries when idle
                      </div>
                    </div>
                  </div>

                  {/* Platform Totals Grid */}
                  <div style={{ background: "#111827", padding: "24px", borderRadius: "12px", border: "1px solid #1f2937", marginBottom: "28px" }}>
                    <h3 style={{ margin: "0 0 16px", fontSize: "1.1rem" }}>Platform-Wide Totals</h3>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px" }}>
                      <div style={{ background: "#1f2937", padding: "16px", borderRadius: "8px" }}>
                        <div style={{ fontSize: "0.78rem", color: "#94a3b8" }}>TOTAL WORKSPACES</div>
                        <div style={{ fontSize: "1.6rem", fontWeight: 700, marginTop: "4px" }}>
                          {adminStats?.totals?.users ?? 1}
                        </div>
                      </div>
                      <div style={{ background: "#1f2937", padding: "16px", borderRadius: "8px" }}>
                        <div style={{ fontSize: "0.78rem", color: "#94a3b8" }}>TOTAL CAMPAIGN BATCHES</div>
                        <div style={{ fontSize: "1.6rem", fontWeight: 700, marginTop: "4px", color: "#38bdf8" }}>
                          {adminStats?.totals?.batches ?? batches.length}
                        </div>
                      </div>
                      <div style={{ background: "#1f2937", padding: "16px", borderRadius: "8px" }}>
                        <div style={{ fontSize: "0.78rem", color: "#94a3b8" }}>TOTAL LEADS MANAGED</div>
                        <div style={{ fontSize: "1.6rem", fontWeight: 700, marginTop: "4px", color: "#22c55e" }}>
                          {adminStats?.totals?.contacts ?? contacts.length}
                        </div>
                      </div>
                      <div style={{ background: "#1f2937", padding: "16px", borderRadius: "8px" }}>
                        <div style={{ fontSize: "0.78rem", color: "#94a3b8" }}>ACTIVE SENDER RELAYS</div>
                        <div style={{ fontSize: "1.6rem", fontWeight: 700, marginTop: "4px", color: "#c084fc" }}>
                          {adminStats?.totals?.sender_relays ?? relays.length}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

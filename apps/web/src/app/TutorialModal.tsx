"use client";

import React, { useState } from "react";
import {
  BookOpen,
  X,
  Copy,
  Check,
  ExternalLink,
  ShieldCheck,
  Zap,
  Layers,
  Mail,
  Sparkles,
  Key,
  Activity,
  Crown,
  CheckCircle2,
  AlertCircle,
  Info,
  ChevronRight,
  ArrowRight,
  FileText,
  Server,
  Database,
  Lock,
} from "lucide-react";

export type TutorialTab = "relay" | "contacts" | "campaigns" | "ai" | "overview" | "admin";

interface TutorialModalProps {
  initialTab?: TutorialTab;
  onClose: () => void;
}

export const APPS_SCRIPT_RELAY_CODE = `/**
 * MailOrbit Google Apps Script Email Relay
 * 
 * Secure, per-user email relay deployed as a Google Apps Script Web App.
 * Relays cold emails via the user's personal Gmail account using MailApp.
 * 
 * Security & Reliability Features:
 * 1. Token in Script Properties: Stored in PropertiesService ("RELAY_AUTH_TOKEN"), NEVER hardcoded.
 * 2. Quota Guard: Checks MailApp.getRemainingDailyQuota() and returns QUOTA_EXCEEDED if 0.
 * 3. Idempotency: Uses CacheService to reject duplicate idempotency keys (persists up to 6 hours).
 * 4. Recipient Validation: Strict email regex check before sending.
 * 5. Attachment Size Guard: Enforces Google's 25 MB total attachment limit.
 * 6. Zero Secret Logging: Never logs auth tokens or request credentials to Logger/Cloud Logs.
 */

// Basic email validation regex conforming to RFC 5322 standard
const EMAIL_REGEX = /^[a-zA-Z0-9.!#$%&'*+/=?^_\`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;
const MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024; // 25 MB limit for Gmail

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return jsonResponse({
        success: false,
        error: "MISSING_PAYLOAD",
        message: "No POST body received."
      }, 400);
    }

    let payload;
    try {
      payload = JSON.parse(e.postData.contents);
    } catch (parseErr) {
      return jsonResponse({
        success: false,
        error: "INVALID_JSON",
        message: "Could not parse request body as JSON."
      }, 400);
    }

    // 1. Verify Secret Auth Token from Script Properties
    const scriptProps = PropertiesService.getScriptProperties();
    const configuredToken = scriptProps.getProperty("RELAY_AUTH_TOKEN");

    if (!configuredToken) {
      return jsonResponse({
        success: false,
        error: "NOT_CONFIGURED",
        message: "Relay auth token is not configured in Script Properties."
      }, 500);
    }

    const incomingToken = payload.token;
    if (!incomingToken || incomingToken !== configuredToken) {
      return jsonResponse({
        success: false,
        error: "UNAUTHORIZED",
        message: "Invalid or missing relay authentication token."
      }, 401);
    }

    // 2. Daily Quota Guard
    const remainingQuota = MailApp.getRemainingDailyQuota();
    if (remainingQuota <= 0) {
      return jsonResponse({
        success: false,
        error: "QUOTA_EXCEEDED",
        remaining_quota: 0,
        message: "Gmail daily sending quota has been reached for today."
      }, 429);
    }

    // 3. Idempotency Check
    const idempotencyKey = payload.idempotency_key;
    if (idempotencyKey) {
      const cache = CacheService.getScriptCache();
      const existing = cache.get("idem_" + idempotencyKey);
      if (existing) {
        return jsonResponse({
          success: false,
          error: "DUPLICATE_REQUEST",
          idempotency_key: idempotencyKey,
          message: "Request with this idempotency key was already processed."
        }, 409);
      }
    }

    // 4. Validate Recipient Email Address
    const recipient = (payload.to || "").trim();
    if (!recipient || !EMAIL_REGEX.test(recipient)) {
      return jsonResponse({
        success: false,
        error: "INVALID_EMAIL",
        message: "Invalid recipient email address: " + recipient
      }, 400);
    }

    // 5. Validate and Prepare Mail Options
    const subject = payload.subject || "(No Subject)";
    const htmlBody = payload.html_body || payload.body || "";
    const plainBody = payload.plain_body || stripHtml(htmlBody);

    const mailOptions = {
      to: recipient,
      subject: subject,
      body: plainBody,
      htmlBody: htmlBody
    };

    if (payload.reply_to) {
      mailOptions.replyTo = payload.reply_to;
    }
    if (payload.cc) {
      mailOptions.cc = payload.cc;
    }
    if (payload.bcc) {
      mailOptions.bcc = payload.bcc;
    }

    // 6. Handle Attachments (with 25 MB Guard)
    let totalAttachmentBytes = 0;
    if (payload.attachments && Array.isArray(payload.attachments)) {
      const blobs = [];
      for (let i = 0; i < payload.attachments.length; i++) {
        const att = payload.attachments[i];
        if (!att.filename || !att.base64_content) {
          continue;
        }

        const decodedBytes = Utilities.base64Decode(att.base64_content);
        totalAttachmentBytes += decodedBytes.length;

        if (totalAttachmentBytes > MAX_ATTACHMENT_BYTES) {
          return jsonResponse({
            success: false,
            error: "ATTACHMENT_TOO_LARGE",
            message: "Total attachments exceed the 25 MB limit (" + totalAttachmentBytes + " bytes)."
          }, 413);
        }

        const blob = Utilities.newBlob(decodedBytes, att.mime_type || "application/octet-stream", att.filename);
        blobs.push(blob);
      }
      if (blobs.length > 0) {
        mailOptions.attachments = blobs;
      }
    }

    // 7. Dispatch Mail
    MailApp.sendEmail(mailOptions);

    // 8. Cache Idempotency Key (cached for 6 hours = 21600 seconds)
    if (idempotencyKey) {
      try {
        CacheService.getScriptCache().put("idem_" + idempotencyKey, "SENT", 21600);
      } catch (cacheErr) {
        // Cache error shouldn't abort a successful send
      }
    }

    return jsonResponse({
      success: true,
      message: "Email dispatched successfully via Gmail MailApp",
      recipient: recipient,
      remaining_quota: MailApp.getRemainingDailyQuota()
    }, 200);

  } catch (err) {
    return jsonResponse({
      success: false,
      error: "SEND_FAILED",
      message: err.toString()
    }, 500);
  }
}

function doGet(e) {
  // Simple health check endpoint for relay verification
  const remainingQuota = MailApp.getRemainingDailyQuota();
  return jsonResponse({
    status: "ok",
    service: "MailOrbit Google Apps Script Relay",
    version: "1.0.0",
    remaining_quota: remainingQuota
  }, 200);
}

function jsonResponse(data, statusCode) {
  const output = ContentService.createTextOutput(JSON.stringify(data));
  output.setMimeType(ContentService.MimeType.JSON);
  return output;
}

function stripHtml(html) {
  return html.replace(/<[^>]*>?/gm, " ").replace(/\\s+/g, " ").trim();
}`;

export const SAMPLE_CSV_CONTENT = `email,name,company,role,notes
alex.turner@techcorp.io,Alex Turner,TechCorp,Engineering VP,Met at TechCrunch 2026
sarah.lin@growthscale.com,Sarah Lin,GrowthScale,Founder,Series A AI startup
david.ross@acmeventures.com,David Ross,Acme Ventures,Partner,B2B SaaS focus
priya.patel@innovatelabs.ai,Priya Patel,InnovateLabs,CTO,Building LLM agents
michael.chang@apexsystems.dev,Michael Chang,Apex Systems,Head of Talent,Hiring Senior AI Engineers`;

export const SAMPLE_COLD_EMAIL_TEMPLATE = `Subject: Quick question regarding {{company}}'s AI infrastructure, {{name}}

Hi {{name}},

{{icebreaker}}

I've been following {{company}}'s recent progress with autonomous agents. As a full-stack & AI engineer with hands-on experience building resilient distributed architectures and production GenAI pipelines (including Google Antigravity & real-time agentic workflows), I noticed potential synergy with your current roadmap.

I built a zero-password cold outreach engine that achieves 100% Google SPF/DKIM alignment with zero third-party email API fees. Would you be open to a 10-minute sync this Thursday or Friday to connect?

Best regards,
Vikas Dangi
Portfolio: https://github.com/Vikas003dangi`;

export const SAMPLE_GEMINI_PROMPT_TEMPLATE = `Analyze the target company / job description against candidate Vikas Dangi's profile.

Candidate Strengths:
- B.Tech CSE (SATI Vidisha, CGPA 8.61), 4x Oracle Cloud Certified, Oracle GenAI Certified.
- Built MailOrbit (FastAPI + Neon PostgreSQL + Google Apps Script HTTPS:443 zero-password relay).
- Built ABCD Campus ERP (live on Google Play Store, 500+ active university users).
- Resilient distributed queues, idempotency caches, and context-aware LLM agents.

Task:
Extract top 3 matching requirements from the JD and generate a punchy 2-sentence cold-email opening icebreaker.
Rules: Authentic tone, no boilerplate fluff, mention 1 concrete technical milestone.`;

export default function TutorialModal({ initialTab = "relay", onClose }: TutorialModalProps) {
  const [activeTab, setActiveTab] = useState<TutorialTab>(initialTab);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2500);
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 9999,
        background: "rgba(3, 7, 18, 0.88)",
        backdropFilter: "blur(10px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "#0b1329",
          border: "1px solid #1e293b",
          borderRadius: "16px",
          maxWidth: "1050px",
          width: "100%",
          maxHeight: "92vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 25px 60px -15px rgba(0, 0, 0, 0.85), 0 0 40px rgba(56, 189, 248, 0.12)",
          overflow: "hidden",
        }}
      >
        {/* Header Bar */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid #1e293b",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "linear-gradient(to right, #0f172a, #111e38)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "42px",
                height: "42px",
                borderRadius: "10px",
                background: "linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(129, 140, 248, 0.2))",
                border: "1px solid rgba(56, 189, 248, 0.4)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#38bdf8",
              }}
            >
              <BookOpen size={22} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <h2 style={{ margin: 0, fontSize: "1.3rem", fontWeight: 700, color: "#ffffff" }}>
                  MailOrbit Architecture & Tutorial Manual
                </h2>
                <span
                  style={{
                    fontSize: "0.68rem",
                    padding: "3px 8px",
                    borderRadius: "12px",
                    background: "rgba(56, 189, 248, 0.15)",
                    color: "#38bdf8",
                    border: "1px solid rgba(56, 189, 248, 0.3)",
                    fontWeight: 700,
                    letterSpacing: "0.05em",
                  }}
                >
                  INTERACTIVE FLOWCHARTS & GUIDES
                </span>
              </div>
              <p style={{ margin: "3px 0 0", fontSize: "0.84rem", color: "#94a3b8" }}>
                Complete operational documentation, visual architecture flowcharts, and 1-click deployment code.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            aria-label="Close Guide"
            style={{
              background: "#1e293b",
              border: "1px solid #334155",
              color: "#94a3b8",
              width: "36px",
              height: "36px",
              borderRadius: "8px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Section Navigation Pills */}
        <div
          style={{
            display: "flex",
            gap: "8px",
            padding: "12px 24px",
            background: "#080e1e",
            borderBottom: "1px solid #1e293b",
            overflowX: "auto",
          }}
        >
          <button
            onClick={() => setActiveTab("relay")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 14px",
              borderRadius: "8px",
              fontSize: "0.82rem",
              fontWeight: 600,
              cursor: "pointer",
              border: activeTab === "relay" ? "1px solid #0284c7" : "1px solid #1e293b",
              background: activeTab === "relay" ? "rgba(2, 132, 199, 0.2)" : "#0f172a",
              color: activeTab === "relay" ? "#38bdf8" : "#94a3b8",
              whiteSpace: "nowrap",
            }}
          >
            <Key size={14} />
            1. Sender Relay & Apps Script
          </button>

          <button
            onClick={() => setActiveTab("contacts")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 14px",
              borderRadius: "8px",
              fontSize: "0.82rem",
              fontWeight: 600,
              cursor: "pointer",
              border: activeTab === "contacts" ? "1px solid #0284c7" : "1px solid #1e293b",
              background: activeTab === "contacts" ? "rgba(2, 132, 199, 0.2)" : "#0f172a",
              color: activeTab === "contacts" ? "#38bdf8" : "#94a3b8",
              whiteSpace: "nowrap",
            }}
          >
            <Mail size={14} />
            2. Leads CSV & Dynamic Fallback
          </button>

          <button
            onClick={() => setActiveTab("campaigns")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 14px",
              borderRadius: "8px",
              fontSize: "0.82rem",
              fontWeight: 600,
              cursor: "pointer",
              border: activeTab === "campaigns" ? "1px solid #0284c7" : "1px solid #1e293b",
              background: activeTab === "campaigns" ? "rgba(2, 132, 199, 0.2)" : "#0f172a",
              color: activeTab === "campaigns" ? "#38bdf8" : "#94a3b8",
              whiteSpace: "nowrap",
            }}
          >
            <Layers size={14} />
            3. Campaigns, Batches & Pacing
          </button>

          <button
            onClick={() => setActiveTab("ai")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 14px",
              borderRadius: "8px",
              fontSize: "0.82rem",
              fontWeight: 600,
              cursor: "pointer",
              border: activeTab === "ai" ? "1px solid #0284c7" : "1px solid #1e293b",
              background: activeTab === "ai" ? "rgba(2, 132, 199, 0.2)" : "#0f172a",
              color: activeTab === "ai" ? "#38bdf8" : "#94a3b8",
              whiteSpace: "nowrap",
            }}
          >
            <Sparkles size={14} />
            4. AI Personalizer & BYOK
          </button>

          <button
            onClick={() => setActiveTab("overview")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 14px",
              borderRadius: "8px",
              fontSize: "0.82rem",
              fontWeight: 600,
              cursor: "pointer",
              border: activeTab === "overview" ? "1px solid #0284c7" : "1px solid #1e293b",
              background: activeTab === "overview" ? "rgba(2, 132, 199, 0.2)" : "#0f172a",
              color: activeTab === "overview" ? "#38bdf8" : "#94a3b8",
              whiteSpace: "nowrap",
            }}
          >
            <Activity size={14} />
            5. Full Platform Topology
          </button>

          <button
            onClick={() => setActiveTab("admin")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 14px",
              borderRadius: "8px",
              fontSize: "0.82rem",
              fontWeight: 600,
              cursor: "pointer",
              border: activeTab === "admin" ? "1px solid #f59e0b" : "1px solid #1e293b",
              background: activeTab === "admin" ? "rgba(245, 158, 11, 0.15)" : "#0f172a",
              color: activeTab === "admin" ? "#fbbf24" : "#94a3b8",
              whiteSpace: "nowrap",
            }}
          >
            <Crown size={14} />
            6. Superuser Control Deck
          </button>
        </div>

        {/* Scrollable Content Area */}
        <div style={{ flex: 1, overflowY: "auto", padding: "28px 32px" }}>
          {activeTab === "relay" && (
            <div>
              {/* Title & Concept */}
              <div style={{ marginBottom: "24px" }}>
                <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#38bdf8", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Module 1: Zero-Password Egress Architecture
                </span>
                <h3 style={{ fontSize: "1.6rem", fontWeight: 800, color: "#ffffff", margin: "6px 0 10px" }}>
                  Google Apps Script Egress Relay Setup
                </h3>
                <p style={{ color: "#cbd5e1", fontSize: "0.95rem", lineHeight: 1.6, margin: 0 }}>
                  Why does MailOrbit use a Google Apps Script relay? Cloud providers (Render, AWS, DigitalOcean) host datacenter IPs that are permanently throttled or flagged as spam by Google, Microsoft, and Yahoo if sent directly via SMTP. 
                  By deploying our open-source Apps Script proxy, all emails originate directly from your authenticated Gmail account over secure HTTPS:443 with <strong>100% SPF, DKIM, and DMARC alignment</strong>, zero third-party email API subscriptions, and zero app password storage.
                </p>
              </div>

              {/* Architectural SVG Flowchart */}
              <div style={{ background: "#060d1f", borderRadius: "12px", border: "1px solid #1e293b", padding: "20px", marginBottom: "28px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.85rem", fontWeight: 700, color: "#e2e8f0" }}>
                    <Zap size={16} color="#38bdf8" />
                    Interactive Architecture Flowchart: Zero-Password Relay
                  </div>
                  <span style={{ fontSize: "0.72rem", color: "#64748b" }}>HTTPS Port 443 Only (No SMTP Port 25/587)</span>
                </div>

                <div style={{ overflowX: "auto" }}>
                  <svg viewBox="0 0 860 210" style={{ width: "100%", minWidth: "750px", height: "auto" }}>
                    <defs>
                      <linearGradient id="blueNode" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#0284c7" />
                        <stop offset="100%" stopColor="#0369a1" />
                      </linearGradient>
                      <linearGradient id="amberNode" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#f59e0b" />
                        <stop offset="100%" stopColor="#d97706" />
                      </linearGradient>
                      <linearGradient id="greenNode" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#10b981" />
                        <stop offset="100%" stopColor="#059669" />
                      </linearGradient>
                      <linearGradient id="purpleNode" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#8b5cf6" />
                        <stop offset="100%" stopColor="#6d28d9" />
                      </linearGradient>
                      <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                        <path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8" />
                      </marker>
                    </defs>

                    {/* Step 1: Render FastAPI Engine */}
                    <rect x="20" y="45" width="165" height="110" rx="10" fill="url(#blueNode)" stroke="#38bdf8" strokeWidth="1.5" />
                    <text x="102" y="78" fill="#ffffff" fontWeight="700" fontSize="13" textAnchor="middle">MailOrbit Engine</text>
                    <text x="102" y="98" fill="#e0f2fe" fontSize="10" textAnchor="middle">FastAPI on Render</text>
                    <text x="102" y="118" fill="#bae6fd" fontSize="9.5" textAnchor="middle">Batch Worker /tick</text>
                    <text x="102" y="136" fill="#7dd3fc" fontSize="9" fontWeight="600" textAnchor="middle">Neon PG Row Lock</text>

                    {/* Arrow 1 */}
                    <line x1="185" y1="100" x2="245" y2="100" stroke="#38bdf8" strokeWidth="2.5" markerEnd="url(#arrow)" strokeDasharray="5,3" />
                    <text x="215" y="88" fill="#38bdf8" fontSize="9" fontWeight="700" textAnchor="middle">POST :443</text>
                    <text x="215" y="118" fill="#94a3b8" fontSize="8" textAnchor="middle">JSON + Token</text>

                    {/* Step 2: Google Apps Script Web App */}
                    <rect x="250" y="45" width="175" height="110" rx="10" fill="url(#amberNode)" stroke="#fcd34d" strokeWidth="1.5" />
                    <text x="337" y="78" fill="#ffffff" fontWeight="700" fontSize="13" textAnchor="middle">Apps Script Web App</text>
                    <text x="337" y="98" fill="#fef3c7" fontSize="10" textAnchor="middle">script.google.com</text>
                    <text x="337" y="118" fill="#fde68a" fontSize="9.5" textAnchor="middle">Token Verification</text>
                    <text x="337" y="136" fill="#fef08a" fontSize="9" fontWeight="600" textAnchor="middle">Idempotency & Quota</text>

                    {/* Arrow 2 */}
                    <line x1="425" y1="100" x2="485" y2="100" stroke="#38bdf8" strokeWidth="2.5" markerEnd="url(#arrow)" strokeDasharray="5,3" />
                    <text x="455" y="88" fill="#38bdf8" fontSize="9" fontWeight="700" textAnchor="middle">Internal API</text>
                    <text x="455" y="118" fill="#94a3b8" fontSize="8" textAnchor="middle">MailApp.send</text>

                    {/* Step 3: Google Gmail Core */}
                    <rect x="490" y="45" width="165" height="110" rx="10" fill="url(#greenNode)" stroke="#6ee7b7" strokeWidth="1.5" />
                    <text x="572" y="78" fill="#ffffff" fontWeight="700" fontSize="13" textAnchor="middle">Gmail Infrastructure</text>
                    <text x="572" y="98" fill="#d1fae5" fontSize="10" textAnchor="middle">Google Mail MX Core</text>
                    <text x="572" y="118" fill="#a7f3d0" fontSize="9.5" textAnchor="middle">Native DKIM / SPF</text>
                    <text x="572" y="136" fill="#bbf7d0" fontSize="9" fontWeight="600" textAnchor="middle">100 / 1500 daily quota</text>

                    {/* Arrow 3 */}
                    <line x1="655" y1="100" x2="715" y2="100" stroke="#38bdf8" strokeWidth="2.5" markerEnd="url(#arrow)" strokeDasharray="5,3" />
                    <text x="685" y="88" fill="#38bdf8" fontSize="9" fontWeight="700" textAnchor="middle">Delivery</text>
                    <text x="685" y="118" fill="#94a3b8" fontSize="8" textAnchor="middle">High Reputation</text>

                    {/* Step 4: Recipient Inbox */}
                    <rect x="720" y="45" width="125" height="110" rx="10" fill="url(#purpleNode)" stroke="#c4b5fd" strokeWidth="1.5" />
                    <text x="782" y="78" fill="#ffffff" fontWeight="700" fontSize="13" textAnchor="middle">Primary Inbox</text>
                    <text x="782" y="98" fill="#ede9fe" fontSize="10" textAnchor="middle">Target HR / Lead</text>
                    <text x="782" y="118" fill="#ddd6fe" fontSize="9" textAnchor="middle">0% Spam Flag</text>
                    <text x="782" y="136" fill="#e9d5ff" fontSize="9" fontWeight="600" textAnchor="middle">RFC-8058 Header</text>

                    {/* Safety Circuit Breaker Label Bar */}
                    <rect x="20" y="175" width="825" height="26" rx="6" fill="#0f172a" stroke="#334155" strokeWidth="1" />
                    <text x="432" y="192" fill="#94a3b8" fontSize="10" fontWeight="600" textAnchor="middle">
                      Safety Circuit Breaker: Auto-pauses batch if 3 consecutive errors occur or daily quota reaches 0
                    </text>
                  </svg>
                </div>
              </div>

              {/* Step by Step Guide */}
              <div style={{ display: "flex", flexDirection: "column", gap: "20px", marginBottom: "32px" }}>
                <h4 style={{ fontSize: "1.15rem", fontWeight: 700, color: "#ffffff", margin: "0 0 6px" }}>
                  5-Minute Setup Walkthrough:
                </h4>

                {/* Step 1 */}
                <div style={{ display: "flex", gap: "16px", background: "#0e172e", padding: "18px", borderRadius: "10px", border: "1px solid #1e293b" }}>
                  <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "#0284c7", color: "#ffffff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: "0.9rem", flexShrink: 0 }}>
                    1
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, color: "#ffffff", fontSize: "0.98rem", marginBottom: "4px" }}>
                      Open Google Apps Script
                    </div>
                    <p style={{ color: "#94a3b8", fontSize: "0.88rem", margin: "0 0 10px", lineHeight: 1.5 }}>
                      Navigate to <a href="https://script.google.com" target="_blank" rel="noreferrer" style={{ color: "#38bdf8", textDecoration: "underline" }}>script.google.com</a> in your browser. Sign in with the exact Gmail or Google Workspace account you intend to send cold emails from. Click <strong>+ New project</strong> in the top left corner, and name it <strong>MailOrbit Relay</strong>.
                    </p>
                  </div>
                </div>

                {/* Step 2 */}
                <div style={{ display: "flex", gap: "16px", background: "#0e172e", padding: "18px", borderRadius: "10px", border: "1px solid #1e293b" }}>
                  <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "#0284c7", color: "#ffffff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: "0.9rem", flexShrink: 0 }}>
                    2
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                      <div style={{ fontWeight: 700, color: "#ffffff", fontSize: "0.98rem" }}>
                        Paste the Open-Source Relay Code
                      </div>
                      <button
                        onClick={() => handleCopy(APPS_SCRIPT_RELAY_CODE, "relay-code")}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                          background: copiedId === "relay-code" ? "#16a34a" : "#0284c7",
                          color: "#ffffff",
                          border: "none",
                          padding: "6px 12px",
                          borderRadius: "6px",
                          fontSize: "0.78rem",
                          fontWeight: 700,
                          cursor: "pointer",
                          transition: "all 0.2s ease",
                        }}
                      >
                        {copiedId === "relay-code" ? <Check size={14} /> : <Copy size={14} />}
                        {copiedId === "relay-code" ? "Copied Relay Script!" : "Copy Full Script (197 Lines)"}
                      </button>
                    </div>
                    <p style={{ color: "#94a3b8", fontSize: "0.88rem", margin: "0 0 12px", lineHeight: 1.5 }}>
                      Erase all default template code inside the editor (`myFunction()`), and paste the entire script below. Press <strong>Ctrl + S</strong> (or Cmd + S) to save.
                    </p>
                    <div style={{ maxHeight: "200px", overflowY: "auto", background: "#060913", border: "1px solid #1e293b", borderRadius: "8px", padding: "12px", fontFamily: "monospace", fontSize: "0.78rem", color: "#93c5fd" }}>
                      <pre style={{ margin: 0 }}>{APPS_SCRIPT_RELAY_CODE.slice(0, 1100)}... (click button above to copy full 197 lines)</pre>
                    </div>
                  </div>
                </div>

                {/* Step 3 */}
                <div style={{ display: "flex", gap: "16px", background: "#0e172e", padding: "18px", borderRadius: "10px", border: "1px solid #1e293b" }}>
                  <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "#0284c7", color: "#ffffff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: "0.9rem", flexShrink: 0 }}>
                    3
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, color: "#ffffff", fontSize: "0.98rem", marginBottom: "4px" }}>
                      Configure Your Secret Auth Token (Never in Code!)
                    </div>
                    <p style={{ color: "#94a3b8", fontSize: "0.88rem", margin: "0 0 8px", lineHeight: 1.5 }}>
                      In the left sidebar of the Google Apps Script editor, click the <strong>Gear icon (Project Settings)</strong>. Scroll down to <strong>Script Properties</strong> and click <strong>Add script property</strong>:
                    </p>
                    <ul style={{ color: "#cbd5e1", fontSize: "0.85rem", margin: "0 0 8px", paddingLeft: "20px" }}>
                      <li><strong>Property:</strong> <code style={{ color: "#38bdf8", background: "#1e293b", padding: "2px 6px", borderRadius: "4px" }}>RELAY_AUTH_TOKEN</code></li>
                      <li><strong>Value:</strong> Choose any strong random secret token (e.g., <code style={{ color: "#fcd34d", background: "#1e293b", padding: "2px 6px", borderRadius: "4px" }}>mo_relay_sec_9a8b7c6d5e</code>)</li>
                    </ul>
                    <p style={{ color: "#94a3b8", fontSize: "0.84rem", margin: 0 }}>
                      Click <strong>Save script properties</strong>. This secret prevents unauthorized calls to your Web App.
                    </p>
                  </div>
                </div>

                {/* Step 4 */}
                <div style={{ display: "flex", gap: "16px", background: "#0e172e", padding: "18px", borderRadius: "10px", border: "1px solid #1e293b" }}>
                  <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "#0284c7", color: "#ffffff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: "0.9rem", flexShrink: 0 }}>
                    4
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, color: "#ffffff", fontSize: "0.98rem", marginBottom: "4px" }}>
                      Deploy as Web App
                    </div>
                    <p style={{ color: "#94a3b8", fontSize: "0.88rem", margin: "0 0 8px", lineHeight: 1.5 }}>
                      Click the blue <strong>Deploy</strong> button in the top right, then select <strong>New deployment</strong>:
                    </p>
                    <ul style={{ color: "#cbd5e1", fontSize: "0.85rem", margin: "0 0 8px", paddingLeft: "20px" }}>
                      <li>Click the gear icon next to "Select type" and choose <strong>Web app</strong>.</li>
                      <li><strong>Description:</strong> `MailOrbit v1 Relay`</li>
                      <li><strong>Execute as:</strong> <strong>Me (your_email@gmail.com)</strong> <em>(Mandatory: emails will originate from your inbox)</em></li>
                      <li><strong>Who has access:</strong> <strong>Anyone</strong> <em>(Access is secured by your secret token)</em></li>
                    </ul>
                    <p style={{ color: "#94a3b8", fontSize: "0.84rem", margin: 0 }}>
                      Authorize Google permissions when prompted, and copy the generated <strong>Web app URL</strong> (<code style={{ color: "#38bdf8" }}>https://script.google.com/macros/s/.../exec</code>).
                    </p>
                  </div>
                </div>

                {/* Step 5 */}
                <div style={{ display: "flex", gap: "16px", background: "#0e172e", padding: "18px", borderRadius: "10px", border: "1px solid #1e293b" }}>
                  <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "#0284c7", color: "#ffffff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: "0.9rem", flexShrink: 0 }}>
                    5
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, color: "#ffffff", fontSize: "0.98rem", marginBottom: "4px" }}>
                      Paste URL & Secret into MailOrbit
                    </div>
                    <p style={{ color: "#94a3b8", fontSize: "0.88rem", margin: "0 0 8px", lineHeight: 1.5 }}>
                      Return to the <strong>Sender Relay & Keys</strong> section in MailOrbit. Enter your Sender Gmail, Web App URL, and Secret Token, then click <strong>Connect Relay</strong>.
                    </p>
                    <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", background: "rgba(16, 185, 129, 0.15)", color: "#34d399", padding: "6px 12px", borderRadius: "6px", fontSize: "0.82rem", fontWeight: 600 }}>
                      <CheckCircle2 size={14} /> MailOrbit verifies the endpoint via live HTTP GET handshake instantly!
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "contacts" && (
            <div>
              <div style={{ marginBottom: "24px" }}>
                <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#38bdf8", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Module 2: Lead Acquisition & Scrubbing Pipeline
                </span>
                <h3 style={{ fontSize: "1.6rem", fontWeight: 800, color: "#ffffff", margin: "6px 0 10px" }}>
                  Leads CSV Upload & Standby Dynamic Fallback
                </h3>
                <p style={{ color: "#cbd5e1", fontSize: "0.95rem", lineHeight: 1.6, margin: 0 }}>
                  Bad email lists destroy sender domain reputation. MailOrbit enforces automated column normalization, strict RFC-2606 domain filtering (instantly dropping fake/malformed test domains like .test, .invalid, example.com), deduplication, and a <strong>zero-waste standby replacement pool</strong>.
                </p>
              </div>

              {/* Architectural SVG Flowchart */}
              <div style={{ background: "#060d1f", borderRadius: "12px", border: "1px solid #1e293b", padding: "20px", marginBottom: "28px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.85rem", fontWeight: 700, color: "#e2e8f0" }}>
                    <Zap size={16} color="#38bdf8" />
                    Interactive Lead Normalization & Replacement Flowchart
                  </div>
                  <span style={{ fontSize: "0.72rem", color: "#64748b" }}>Automated Quality Guard</span>
                </div>

                <div style={{ overflowX: "auto" }}>
                  <svg viewBox="0 0 860 220" style={{ width: "100%", minWidth: "750px", height: "auto" }}>
                    <defs>
                      <marker id="arrow2" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                        <path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8" />
                      </marker>
                    </defs>

                    {/* Step 1: Raw CSV */}
                    <rect x="20" y="55" width="150" height="95" rx="8" fill="#1e293b" stroke="#38bdf8" strokeWidth="1.5" />
                    <text x="95" y="88" fill="#ffffff" fontWeight="700" fontSize="12.5" textAnchor="middle">User Leads CSV</text>
                    <text x="95" y="108" fill="#94a3b8" fontSize="10" textAnchor="middle">UTF-8 File Upload</text>
                    <text x="95" y="126" fill="#38bdf8" fontSize="9" textAnchor="middle">Auto-Column Match</text>

                    {/* Arrow 1 */}
                    <line x1="170" y1="102" x2="225" y2="102" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arrow2)" />

                    {/* Step 2: Sanitation */}
                    <rect x="230" y="55" width="165" height="95" rx="8" fill="#0369a1" stroke="#38bdf8" strokeWidth="1.5" />
                    <text x="312" y="88" fill="#ffffff" fontWeight="700" fontSize="12.5" textAnchor="middle">RFC-2606 Filter</text>
                    <text x="312" y="108" fill="#e0f2fe" fontSize="10" textAnchor="middle">Drops .test, .invalid</text>
                    <text x="312" y="126" fill="#bae6fd" fontSize="9" textAnchor="middle">De-duplicates Records</text>

                    {/* Arrow 2: Split */}
                    <path d="M 395 102 L 440 65" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arrow2)" fill="none" />
                    <path d="M 395 102 L 440 145" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arrow2)" fill="none" />

                    {/* Top Branch: Active 30/day */}
                    <rect x="445" y="20" width="180" height="85" rx="8" fill="#065f46" stroke="#34d399" strokeWidth="1.5" />
                    <text x="535" y="50" fill="#ffffff" fontWeight="700" fontSize="12" textAnchor="middle">Active Dispatch Batch</text>
                    <text x="535" y="70" fill="#d1fae5" fontSize="9.5" textAnchor="middle">Target 30 contacts / day</text>
                    <text x="535" y="88" fill="#a7f3d0" fontSize="8.5" textAnchor="middle">Enforces sender reputation</text>

                    {/* Bottom Branch: Standby Pool */}
                    <rect x="445" y="115" width="180" height="85" rx="8" fill="#312e81" stroke="#818cf8" strokeWidth="1.5" />
                    <text x="535" y="145" fill="#ffffff" fontWeight="700" fontSize="12" textAnchor="middle">Standby Reserve Pool</text>
                    <text x="535" y="165" fill="#e0e7ff" fontSize="9.5" textAnchor="middle">Overflow contacts stored</text>
                    <text x="535" y="183" fill="#c7d2fe" fontSize="8.5" textAnchor="middle">Zero quota loss guarantee</text>

                    {/* Replacement Connector */}
                    <path d="M 535 115 L 535 105" stroke="#f59e0b" strokeWidth="2" strokeDasharray="4,2" markerEnd="url(#arrow2)" />

                    {/* Arrow to Dispatch */}
                    <line x1="625" y1="62" x2="685" y2="62" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arrow2)" />

                    {/* Final Step */}
                    <rect x="690" y="30" width="150" height="150" rx="8" fill="#1e1b4b" stroke="#a855f7" strokeWidth="1.5" />
                    <text x="765" y="65" fill="#ffffff" fontWeight="700" fontSize="12" textAnchor="middle">Autonomous Dispatch</text>
                    <text x="765" y="90" fill="#f3e8ff" fontSize="9.5" textAnchor="middle">Dynamic Replacement:</text>
                    <text x="765" y="110" fill="#d8b4fe" fontSize="8.5" textAnchor="middle">If bounce/failure occurs,</text>
                    <text x="765" y="128" fill="#d8b4fe" fontSize="8.5" textAnchor="middle">instantly promotes next</text>
                    <text x="765" y="146" fill="#c084fc" fontSize="9" fontWeight="700" textAnchor="middle">ready standby contact!</text>
                  </svg>
                </div>
              </div>

              {/* Sample CSV Format & Copy */}
              <div style={{ background: "#0e172e", padding: "20px", borderRadius: "10px", border: "1px solid #1e293b", marginBottom: "24px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <div>
                    <h4 style={{ margin: "0 0 4px", fontSize: "1.05rem", color: "#ffffff", fontWeight: 700 }}>
                      Recommended CSV Schema
                    </h4>
                    <p style={{ margin: 0, fontSize: "0.84rem", color: "#94a3b8" }}>
                      MailOrbit auto-detects columns: `email` (or `work_email`), `name` (or `full_name`), `company`, and `role`.
                    </p>
                  </div>
                  <button
                    onClick={() => handleCopy(SAMPLE_CSV_CONTENT, "sample-csv")}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      background: copiedId === "sample-csv" ? "#16a34a" : "#0284c7",
                      color: "#ffffff",
                      border: "none",
                      padding: "7px 14px",
                      borderRadius: "6px",
                      fontSize: "0.8rem",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    {copiedId === "sample-csv" ? <Check size={14} /> : <Copy size={14} />}
                    {copiedId === "sample-csv" ? "Copied CSV Template!" : "Copy Sample CSV"}
                  </button>
                </div>

                <div style={{ background: "#060913", border: "1px solid #1e293b", borderRadius: "8px", padding: "14px", fontFamily: "monospace", fontSize: "0.82rem", color: "#7dd3fc", overflowX: "auto" }}>
                  <pre style={{ margin: 0 }}>{SAMPLE_CSV_CONTENT}</pre>
                </div>
              </div>
            </div>
          )}

          {activeTab === "campaigns" && (
            <div>
              <div style={{ marginBottom: "24px" }}>
                <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#38bdf8", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Module 3: Pacing, Deliverability & Compliance
                </span>
                <h3 style={{ fontSize: "1.6rem", fontWeight: 800, color: "#ffffff", margin: "6px 0 10px" }}>
                  Smart Batches, Quiet Hours & Unsubscribe Compliance
                </h3>
                <p style={{ color: "#cbd5e1", fontSize: "0.95rem", lineHeight: 1.6, margin: 0 }}>
                  Blasting hundreds of emails simultaneously gets your Gmail account suspended instantly. MailOrbit solves deliverability by auto-slicing contacts into <strong>staggered daily batches of 30</strong>, applying randomized humanized delays (60 to 180 seconds between dispatches), respecting business quiet hours (9:00 AM – 6:00 PM), and appending RFC-8058 compliant one-click unsubscribe headers.
                </p>
              </div>

              {/* Architectural SVG Flowchart */}
              <div style={{ background: "#060d1f", borderRadius: "12px", border: "1px solid #1e293b", padding: "20px", marginBottom: "28px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.85rem", fontWeight: 700, color: "#e2e8f0" }}>
                    <Zap size={16} color="#38bdf8" />
                    Interactive Smart Pacing & Deliverability Safeguards
                  </div>
                  <span style={{ fontSize: "0.72rem", color: "#64748b" }}>Reputation Protection Protocol</span>
                </div>

                <div style={{ overflowX: "auto" }}>
                  <svg viewBox="0 0 860 210" style={{ width: "100%", minWidth: "750px", height: "auto" }}>
                    <defs>
                      <marker id="arrow3" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                        <path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8" />
                      </marker>
                    </defs>

                    {/* Box 1 */}
                    <rect x="20" y="50" width="160" height="100" rx="8" fill="#1e293b" stroke="#818cf8" strokeWidth="1.5" />
                    <text x="100" y="82" fill="#ffffff" fontWeight="700" fontSize="12" textAnchor="middle">Campaign Purpose</text>
                    <text x="100" y="102" fill="#cbd5e1" fontSize="9.5" textAnchor="middle">Dynamic Tokens</text>
                    <text x="100" y="122" fill="#a5b4fc" fontSize="9" textAnchor="middle">{"{{name}}, {{company}}"}</text>

                    {/* Arrow 1 */}
                    <line x1="180" y1="100" x2="230" y2="100" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arrow3)" />

                    {/* Box 2 */}
                    <rect x="235" y="50" width="165" height="100" rx="8" fill="#0f766e" stroke="#2dd4bf" strokeWidth="1.5" />
                    <text x="317" y="82" fill="#ffffff" fontWeight="700" fontSize="12" textAnchor="middle">Batch Slicing Engine</text>
                    <text x="317" y="102" fill="#ccfbf1" fontSize="9.5" textAnchor="middle">Max 30 contacts/day</text>
                    <text x="317" y="122" fill="#99f6e4" fontSize="9" textAnchor="middle">Prevents Gmail bans</text>

                    {/* Arrow 2 */}
                    <line x1="400" y1="100" x2="450" y2="100" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arrow3)" />

                    {/* Box 3 */}
                    <rect x="455" y="50" width="175" height="100" rx="8" fill="#b45309" stroke="#fcd34d" strokeWidth="1.5" />
                    <text x="542" y="82" fill="#ffffff" fontWeight="700" fontSize="12" textAnchor="middle">Quiet Hours & Jitter</text>
                    <text x="542" y="102" fill="#fef3c7" fontSize="9.5" textAnchor="middle">9:00 AM – 6:00 PM local</text>
                    <text x="542" y="122" fill="#fde68a" fontSize="9" textAnchor="middle">Random 60-180s delay</text>

                    {/* Arrow 3 */}
                    <line x1="630" y1="100" x2="680" y2="100" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arrow3)" />

                    {/* Box 4 */}
                    <rect x="685" y="50" width="155" height="100" rx="8" fill="#4c1d95" stroke="#c084fc" strokeWidth="1.5" />
                    <text x="762" y="82" fill="#ffffff" fontWeight="700" fontSize="12" textAnchor="middle">RFC-8058 Injection</text>
                    <text x="762" y="102" fill="#f3e8ff" fontSize="9.5" textAnchor="middle">List-Unsubscribe</text>
                    <text x="762" y="122" fill="#d8b4fe" fontSize="9" textAnchor="middle">Direct Inbox Placement</text>
                  </svg>
                </div>
              </div>

              {/* High-Converting Cold Email Template */}
              <div style={{ background: "#0e172e", padding: "20px", borderRadius: "10px", border: "1px solid #1e293b", marginBottom: "24px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <div>
                    <h4 style={{ margin: "0 0 4px", fontSize: "1.05rem", color: "#ffffff", fontWeight: 700 }}>
                      Tested High-Reply Outreach Template
                    </h4>
                    <p style={{ margin: 0, fontSize: "0.84rem", color: "#94a3b8" }}>
                      Replace tokens with your target recipient variables to optimize engagement.
                    </p>
                  </div>
                  <button
                    onClick={() => handleCopy(SAMPLE_COLD_EMAIL_TEMPLATE, "cold-template")}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      background: copiedId === "cold-template" ? "#16a34a" : "#0284c7",
                      color: "#ffffff",
                      border: "none",
                      padding: "7px 14px",
                      borderRadius: "6px",
                      fontSize: "0.8rem",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    {copiedId === "cold-template" ? <Check size={14} /> : <Copy size={14} />}
                    {copiedId === "cold-template" ? "Copied Email Template!" : "Copy Template"}
                  </button>
                </div>

                <div style={{ background: "#060913", border: "1px solid #1e293b", borderRadius: "8px", padding: "14px", fontFamily: "monospace", fontSize: "0.82rem", color: "#cbd5e1", whiteSpace: "pre-wrap" }}>
                  {SAMPLE_COLD_EMAIL_TEMPLATE}
                </div>
              </div>
            </div>
          )}

          {activeTab === "ai" && (
            <div>
              <div style={{ marginBottom: "24px" }}>
                <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#38bdf8", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Module 4: GenAI Matching & Personalization
                </span>
                <h3 style={{ fontSize: "1.6rem", fontWeight: 800, color: "#ffffff", margin: "6px 0 10px" }}>
                  Bring Your Own Key (BYOK) Gemini AI Personalizer
                </h3>
                <p style={{ color: "#cbd5e1", fontSize: "0.95rem", lineHeight: 1.6, margin: 0 }}>
                  Cold emails fail when they look like robotic spam. MailOrbit features an on-demand JD & Resume semantic matcher powered by Google Gemini 1.5 Flash. Bring your own free API key from Google AI Studio: your key stays encrypted, zero data is trained on your submissions, and high-impact custom hooks are generated in under 2 seconds.
                </p>
              </div>

              {/* Architectural SVG Flowchart */}
              <div style={{ background: "#060d1f", borderRadius: "12px", border: "1px solid #1e293b", padding: "20px", marginBottom: "28px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.85rem", fontWeight: 700, color: "#e2e8f0" }}>
                    <Sparkles size={16} color="#38bdf8" />
                    Interactive Gemini BYOK Context Flowchart
                  </div>
                  <span style={{ fontSize: "0.72rem", color: "#64748b" }}>Zero Data Retention</span>
                </div>

                <div style={{ overflowX: "auto" }}>
                  <svg viewBox="0 0 860 210" style={{ width: "100%", minWidth: "750px", height: "auto" }}>
                    <defs>
                      <marker id="arrow4" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                        <path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8" />
                      </marker>
                    </defs>

                    {/* Inputs */}
                    <rect x="20" y="35" width="160" height="60" rx="8" fill="#1e293b" stroke="#38bdf8" strokeWidth="1" />
                    <text x="100" y="60" fill="#ffffff" fontWeight="700" fontSize="11" textAnchor="middle">Candidate Resume</text>
                    <text x="100" y="78" fill="#94a3b8" fontSize="9" textAnchor="middle">Skills & Achievements</text>

                    <rect x="20" y="115" width="160" height="60" rx="8" fill="#1e293b" stroke="#38bdf8" strokeWidth="1" />
                    <text x="100" y="140" fill="#ffffff" fontWeight="700" fontSize="11" textAnchor="middle">Target JD / Company</text>
                    <text x="100" y="158" fill="#94a3b8" fontSize="9" textAnchor="middle">Role Requirements</text>

                    {/* Lines merging */}
                    <path d="M 180 65 L 235 105" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arrow4)" fill="none" />
                    <path d="M 180 145 L 235 105" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arrow4)" fill="none" />

                    {/* Gemini Engine */}
                    <rect x="245" y="50" width="180" height="110" rx="10" fill="#701a75" stroke="#f472b6" strokeWidth="1.5" />
                    <text x="335" y="85" fill="#ffffff" fontWeight="700" fontSize="13" textAnchor="middle">Gemini 1.5 Flash</text>
                    <text x="335" y="105" fill="#fdf2f8" fontSize="10" textAnchor="middle">BYOK User API Key</text>
                    <text x="335" y="125" fill="#fbcfe8" fontSize="9.5" textAnchor="middle">Semantic Alignment Engine</text>
                    <text x="335" y="142" fill="#f472b6" fontSize="8.5" textAnchor="middle">Zero Model Fine-Tuning</text>

                    {/* Arrow to Output */}
                    <line x1="425" y1="105" x2="485" y2="105" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arrow4)" />

                    {/* Results Box */}
                    <rect x="490" y="50" width="175" height="110" rx="10" fill="#1e1b4b" stroke="#818cf8" strokeWidth="1.5" />
                    <text x="577" y="82" fill="#ffffff" fontWeight="700" fontSize="12" textAnchor="middle">Extracted Synergies</text>
                    <text x="577" y="102" fill="#e0e7ff" fontSize="9.5" textAnchor="middle">1. Key Shared Stack</text>
                    <text x="577" y="120" fill="#c7d2fe" fontSize="9.5" textAnchor="middle">2. Relevant Impact Metric</text>
                    <text x="577" y="138" fill="#a5b4fc" fontSize="9.5" textAnchor="middle">3. 2-Sentence Icebreaker</text>

                    {/* Arrow to Injection */}
                    <line x1="665" y1="105" x2="715" y2="105" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arrow4)" />

                    {/* Final Preview Box */}
                    <rect x="720" y="50" width="125" height="110" rx="10" fill="#064e3b" stroke="#34d399" strokeWidth="1.5" />
                    <text x="782" y="85" fill="#ffffff" fontWeight="700" fontSize="12" textAnchor="middle">Ready Draft</text>
                    <text x="782" y="105" fill="#d1fae5" fontSize="9" textAnchor="middle">Direct Injection</text>
                    <text x="782" y="125" fill="#a7f3d0" fontSize="8.5" textAnchor="middle">Into Today's</text>
                    <text x="782" y="142" fill="#6ee7b7" fontSize="9" fontWeight="700" textAnchor="middle">Batch Queue</text>
                  </svg>
                </div>
              </div>

              {/* Prompt Template */}
              <div style={{ background: "#0e172e", padding: "20px", borderRadius: "10px", border: "1px solid #1e293b", marginBottom: "24px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <div>
                    <h4 style={{ margin: "0 0 4px", fontSize: "1.05rem", color: "#ffffff", fontWeight: 700 }}>
                      Custom Prompt Structure
                    </h4>
                    <p style={{ margin: 0, fontSize: "0.84rem", color: "#94a3b8" }}>
                      Use this prompt in Google AI Studio or directly through the MailOrbit Personalizer input.
                    </p>
                  </div>
                  <button
                    onClick={() => handleCopy(SAMPLE_GEMINI_PROMPT_TEMPLATE, "prompt-template")}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      background: copiedId === "prompt-template" ? "#16a34a" : "#0284c7",
                      color: "#ffffff",
                      border: "none",
                      padding: "7px 14px",
                      borderRadius: "6px",
                      fontSize: "0.8rem",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    {copiedId === "prompt-template" ? <Check size={14} /> : <Copy size={14} />}
                    {copiedId === "prompt-template" ? "Copied Prompt!" : "Copy Prompt Template"}
                  </button>
                </div>

                <div style={{ background: "#060913", border: "1px solid #1e293b", borderRadius: "8px", padding: "14px", fontFamily: "monospace", fontSize: "0.82rem", color: "#cbd5e1", whiteSpace: "pre-wrap" }}>
                  {SAMPLE_GEMINI_PROMPT_TEMPLATE}
                </div>
              </div>
            </div>
          )}

          {activeTab === "overview" && (
            <div>
              <div style={{ marginBottom: "24px" }}>
                <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#38bdf8", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Module 5: End-to-End System Topology
                </span>
                <h3 style={{ fontSize: "1.6rem", fontWeight: 800, color: "#ffffff", margin: "6px 0 10px" }}>
                  Complete MailOrbit Lifecycle & Architecture
                </h3>
                <p style={{ color: "#cbd5e1", fontSize: "0.95rem", lineHeight: 1.6, margin: 0 }}>
                  MailOrbit runs as a unified single-origin application deployed on Render. The Next.js client is statically pre-rendered and served directly from root (`/`), calling relative endpoints under `/api/v1` with zero cross-origin latency and strict SameSite cookies.
                </p>
              </div>

              {/* Architectural SVG Flowchart */}
              <div style={{ background: "#060d1f", borderRadius: "12px", border: "1px solid #1e293b", padding: "20px", marginBottom: "28px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.85rem", fontWeight: 700, color: "#e2e8f0" }}>
                    <Activity size={16} color="#38bdf8" />
                    Unified Host Architecture & Data Lifecycle
                  </div>
                  <span style={{ fontSize: "0.72rem", color: "#64748b" }}>Production Topology</span>
                </div>

                <div style={{ overflowX: "auto" }}>
                  <svg viewBox="0 0 860 230" style={{ width: "100%", minWidth: "750px", height: "auto" }}>
                    <defs>
                      <marker id="arrow5" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                        <path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8" />
                      </marker>
                    </defs>

                    {/* Single-Origin Render Service Box */}
                    <rect x="15" y="25" width="430" height="180" rx="12" fill="#0b172e" stroke="#0284c7" strokeWidth="2" strokeDasharray="6,3" />
                    <text x="35" y="50" fill="#38bdf8" fontWeight="800" fontSize="12">Render Web Service (Single-Origin: mailorbit-api-nrxf.onrender.com)</text>

                    {/* Next.js Box */}
                    <rect x="35" y="70" width="170" height="115" rx="8" fill="#1e293b" stroke="#38bdf8" strokeWidth="1.5" />
                    <text x="120" y="100" fill="#ffffff" fontWeight="700" fontSize="12" textAnchor="middle">Next.js Client SPA</text>
                    <text x="120" y="120" fill="#94a3b8" fontSize="9.5" textAnchor="middle">Mounted at Root ("/")</text>
                    <text x="120" y="140" fill="#94a3b8" fontSize="9" textAnchor="middle">Relative fetch("/api/v1")</text>
                    <text x="120" y="160" fill="#38bdf8" fontSize="8.5" fontWeight="600" textAnchor="middle">SameSite=Lax Cookies</text>

                    {/* Internal Arrow */}
                    <line x1="205" y1="125" x2="255" y2="125" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arrow5)" />

                    {/* FastAPI Box */}
                    <rect x="260" y="70" width="165" height="115" rx="8" fill="#0c4a6e" stroke="#38bdf8" strokeWidth="1.5" />
                    <text x="342" y="100" fill="#ffffff" fontWeight="700" fontSize="12" textAnchor="middle">FastAPI Core Backend</text>
                    <text x="342" y="120" fill="#e0f2fe" fontSize="9.5" textAnchor="middle">Routes: /api/v1/*</text>
                    <text x="342" y="140" fill="#bae6fd" fontSize="9" textAnchor="middle">In-Process Job Queue</text>
                    <text x="342" y="160" fill="#7dd3fc" fontSize="8.5" fontWeight="600" textAnchor="middle">Auto-Batch Partitioning</text>

                    {/* External DB Arrow */}
                    <path d="M 425 105 L 485 75" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arrow5)" fill="none" />

                    {/* Neon Database */}
                    <rect x="495" y="30" width="160" height="90" rx="8" fill="#064e3b" stroke="#34d399" strokeWidth="1.5" />
                    <text x="575" y="60" fill="#ffffff" fontWeight="700" fontSize="12" textAnchor="middle">Neon PostgreSQL 16</text>
                    <text x="575" y="80" fill="#d1fae5" fontSize="9.5" textAnchor="middle">Serverless Auto-Suspend</text>
                    <text x="575" y="98" fill="#6ee7b7" fontSize="8.5" textAnchor="middle">Row-Level SELECT FOR UPDATE</text>

                    {/* Outbound Egress Arrow */}
                    <path d="M 425 145 L 485 175" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arrow5)" fill="none" />

                    {/* Google Apps Script Relay */}
                    <rect x="495" y="130" width="160" height="90" rx="8" fill="#78350f" stroke="#fbbf24" strokeWidth="1.5" />
                    <text x="575" y="160" fill="#ffffff" fontWeight="700" fontSize="12" textAnchor="middle">Google Apps Script</text>
                    <text x="575" y="180" fill="#fef3c7" fontSize="9.5" textAnchor="middle">Personal Gmail Relay</text>
                    <text x="575" y="198" fill="#fde68a" fontSize="8.5" textAnchor="middle">100% SPF/DKIM In-Box</text>

                    {/* Final Arrow */}
                    <line x1="655" y1="175" x2="705" y2="175" stroke="#38bdf8" strokeWidth="2" markerEnd="url(#arrow5)" />

                    {/* Recipients */}
                    <rect x="710" y="130" width="135" height="90" rx="8" fill="#3b0764" stroke="#c084fc" strokeWidth="1.5" />
                    <text x="777" y="160" fill="#ffffff" fontWeight="700" fontSize="12" textAnchor="middle">Lead Recipients</text>
                    <text x="777" y="180" fill="#f3e8ff" fontSize="9.5" textAnchor="middle">Humanized Timing</text>
                    <text x="777" y="198" fill="#d8b4fe" fontSize="8.5" textAnchor="middle">High Response Rates</text>

                    {/* Watchdog Cron (Top Right) */}
                    <rect x="710" y="30" width="135" height="90" rx="8" fill="#1c1917" stroke="#f97316" strokeWidth="1.5" />
                    <text x="777" y="58" fill="#ffffff" fontWeight="700" fontSize="11" textAnchor="middle">cron-job.org</text>
                    <text x="777" y="78" fill="#fed7aa" fontSize="9" textAnchor="middle">Header-Only /tick</text>
                    <text x="777" y="98" fill="#fb923c" fontSize="8.5" textAnchor="middle">X-Tick-Secret Guard</text>
                  </svg>
                </div>
              </div>
            </div>
          )}

          {activeTab === "admin" && (
            <div>
              <div style={{ marginBottom: "24px" }}>
                <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#fbbf24", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Module 6: Superuser Infrastructure Deck
                </span>
                <h3 style={{ fontSize: "1.6rem", fontWeight: 800, color: "#ffffff", margin: "6px 0 10px" }}>
                  Superuser Operational Architecture & Control Deck
                </h3>
                <p style={{ color: "#cbd5e1", fontSize: "0.95rem", lineHeight: 1.6, margin: 0 }}>
                  The Admin Control Deck is strictly restricted to designated superuser emails (<strong>vikassdangi@gmail.com</strong> and <strong>vd19055@gmail.com</strong>). It provides live platform-wide telemetry, user account management, zero-delay manual tick dispatching, and egress connectivity diagnostics.
                </p>
              </div>

              {/* Architectural SVG Flowchart */}
              <div style={{ background: "#060d1f", borderRadius: "12px", border: "1px solid #1e293b", padding: "20px", marginBottom: "28px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.85rem", fontWeight: 700, color: "#fbbf24" }}>
                    <Crown size={16} color="#fbbf24" />
                    Admin Control Deck Security & Execution Flow
                  </div>
                  <span style={{ fontSize: "0.72rem", color: "#64748b" }}>Restricted Superuser Role</span>
                </div>

                <div style={{ overflowX: "auto" }}>
                  <svg viewBox="0 0 860 200" style={{ width: "100%", minWidth: "750px", height: "auto" }}>
                    <defs>
                      <marker id="arrow6" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                        <path d="M 0 0 L 10 5 L 0 10 z" fill="#fbbf24" />
                      </marker>
                    </defs>

                    {/* Node 1 */}
                    <rect x="20" y="45" width="165" height="110" rx="10" fill="#78350f" stroke="#fbbf24" strokeWidth="1.5" />
                    <text x="102" y="78" fill="#ffffff" fontWeight="700" fontSize="13" textAnchor="middle">Superuser Auth</text>
                    <text x="102" y="98" fill="#fef3c7" fontSize="9.5" textAnchor="middle">vikassdangi@gmail.com</text>
                    <text x="102" y="116" fill="#fef3c7" fontSize="9.5" textAnchor="middle">vd19055@gmail.com</text>
                    <text x="102" y="136" fill="#fde68a" fontSize="8.5" fontWeight="600" textAnchor="middle">Strict JWT Verification</text>

                    {/* Arrow 1 */}
                    <line x1="185" y1="100" x2="245" y2="100" stroke="#fbbf24" strokeWidth="2" markerEnd="url(#arrow6)" />

                    {/* Node 2 */}
                    <rect x="250" y="45" width="175" height="110" rx="10" fill="#0f172a" stroke="#38bdf8" strokeWidth="1.5" />
                    <text x="337" y="78" fill="#ffffff" fontWeight="700" fontSize="13" textAnchor="middle">FastAPI Middleware</text>
                    <text x="337" y="98" fill="#e2e8f0" fontSize="10" textAnchor="middle">require_superuser</text>
                    <text x="337" y="118" fill="#94a3b8" fontSize="9.5" textAnchor="middle">Rejects Non-Admins: 403</text>
                    <text x="337" y="136" fill="#38bdf8" fontSize="8.5" textAnchor="middle">Audited Admin Action Log</text>

                    {/* Arrow 2 */}
                    <line x1="425" y1="100" x2="485" y2="100" stroke="#fbbf24" strokeWidth="2" markerEnd="url(#arrow6)" />

                    {/* Node 3 */}
                    <rect x="490" y="45" width="350" height="110" rx="10" fill="#111827" stroke="#22c55e" strokeWidth="1.5" />
                    <text x="665" y="75" fill="#ffffff" fontWeight="700" fontSize="13" textAnchor="middle">Active Admin Control Capabilities</text>
                    <text x="665" y="96" fill="#86efac" fontSize="9.5" textAnchor="middle">✓ User Management: Instant activation & suspension toggles</text>
                    <text x="665" y="114" fill="#86efac" fontSize="9.5" textAnchor="middle">✓ Force Trigger /tick: Immediate queue evaluation without waiting for cron</text>
                    <text x="665" y="132" fill="#86efac" fontSize="9.5" textAnchor="middle">✓ Live Egress Probes: Verify outbound HTTPS:443 network connectivity</text>
                  </svg>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid #1e293b",
            background: "#080e1e",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.82rem", color: "#64748b" }}>
            <Info size={14} />
            <span>All guides are open-source and included in the MailOrbit source repository under <code style={{ color: "#94a3b8" }}>docs/</code>.</span>
          </div>

          <button
            onClick={onClose}
            style={{
              background: "#0284c7",
              color: "#ffffff",
              border: "none",
              padding: "9px 20px",
              borderRadius: "8px",
              fontSize: "0.86rem",
              fontWeight: 700,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            Done & Close Guide
          </button>
        </div>
      </div>
    </div>
  );
}


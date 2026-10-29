"use client";

import React, { useState } from "react";
import {
  Sparkles,
  Send,
  Calendar,
  Key,
  Paperclip,
  CheckCircle2,
  AlertCircle,
  BookOpen,
  ArrowRight,
  ShieldCheck,
  Zap,
} from "lucide-react";

interface AiCopilotSectionProps {
  profile: any;
  aiKeys: any[];
  attachments: any[];
  onDraft: (params: any) => Promise<any>;
  onSend: (sendNow: boolean, params: any) => Promise<any>;
  onSaveKey: (key: string, model: string) => Promise<void>;
  onOpenTutorial: (tab: any) => void;
  isDemoMode?: boolean;
}

export default function AiCopilotSection({
  profile,
  aiKeys,
  attachments,
  onDraft,
  onSend,
  onSaveKey,
  onOpenTutorial,
  isDemoMode = false,
}: AiCopilotSectionProps) {
  // Input fields
  const [recipientsText, setRecipientsText] = useState("");
  const [jdText, setJdText] = useState("");
  const [instructions, setInstructions] = useState("");
  const [subject, setSubject] = useState("");
  const [bodyText, setBodyText] = useState("");
  const [attachResume, setAttachResume] = useState(true);

  // States
  const [drafting, setDrafting] = useState(false);
  const [sending, setSending] = useState(false);
  const [matchScore, setMatchScore] = useState<number | null>(null);
  const [matchedSkills, setMatchedSkills] = useState<string[]>([]);
  const [missingSkills, setMissingSkills] = useState<string[]>([]);
  const [providerUsed, setProviderUsed] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<any>(null);

  // Key state
  const [newKey, setNewKey] = useState("");
  const [keyModel, setKeyModel] = useState("gemini-2.5-flash");
  const [keySaving, setKeySaving] = useState(false);

  const activeKey = aiKeys.find((k) => k.status === "ACTIVE" || k.status === "PENDING_TEST");
  const primaryAttachment = attachments.length > 0 ? attachments[0] : null;

  const handleRunDraft = async () => {
    setDrafting(true);
    setFeedback(null);
    try {
      const firstEmail = recipientsText.split(/[\n,;]+/)[0]?.trim();
      const res = await onDraft({
        job_description: jdText || undefined,
        instructions: instructions || undefined,
        recipient_email: firstEmail || undefined,
      });
      if (res) {
        setSubject(res.subject);
        setBodyText(res.body_text);
        setMatchScore(res.match_score || 0);
        setMatchedSkills(res.matched_skills || []);
        setMissingSkills(res.missing_skills || []);
        setProviderUsed(res.provider || "template");
      }
    } catch (err: any) {
      setFeedback({ error: err.message });
    } finally {
      setDrafting(false);
    }
  };

  const handleRunSend = async (sendNow: boolean) => {
    if (!recipientsText.trim()) {
      setFeedback({ error: "Please enter at least one recipient email address." });
      return;
    }
    if (!subject.trim() || !bodyText.trim()) {
      setFeedback({ error: "Please provide a subject line and email body." });
      return;
    }

    setSending(true);
    setFeedback(null);
    try {
      const recList = recipientsText
        .split(/[\n,;]+/)
        .map((s) => s.trim())
        .filter(Boolean);

      const res = await onSend(sendNow, {
        recipients: recList,
        subject,
        body_text: bodyText,
        attach_resume: attachResume,
      });
      setFeedback({ success: true, ...res });
    } catch (err: any) {
      setFeedback({ error: err.message });
    } finally {
      setSending(false);
    }
  };

  const handleSaveKeySubmit = async () => {
    if (!newKey.trim()) return;
    setKeySaving(true);
    try {
      await onSaveKey(newKey.trim(), keyModel);
      setNewKey("");
    } finally {
      setKeySaving(false);
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 6px" }}>
            AI Helping Hand & Quick Outreach
          </h1>
          <p style={{ color: "#94a3b8", fontSize: "0.92rem", margin: 0 }}>
            Generate high-converting personalized cold emails from Job Descriptions with ATS keyword match, resume attachment, and instant or scheduled dispatch.
          </p>
        </div>
        <button
          onClick={() => onOpenTutorial("ai")}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            background: "rgba(56, 189, 248, 0.12)",
            border: "1px solid #0284c7",
            color: "#38bdf8",
            padding: "9px 16px",
            borderRadius: "8px",
            fontWeight: 600,
            fontSize: "0.85rem",
            cursor: "pointer",
          }}
        >
          <BookOpen size={16} />
          📘 AI Copilot & Prompting Guide
        </button>
      </div>

      {feedback && (
        <div
          style={{
            background: feedback.error ? "rgba(239, 68, 68, 0.15)" : "rgba(34, 197, 94, 0.15)",
            border: `1px solid ${feedback.error ? "#ef4444" : "#22c55e"}`,
            borderRadius: "8px",
            padding: "14px 18px",
            marginBottom: "20px",
            fontSize: "0.88rem",
            color: feedback.error ? "#fca5a5" : "#86efac",
            display: "flex",
            alignItems: "center",
            gap: "10px",
          }}
        >
          {feedback.error ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}
          <div>
            <strong>{feedback.error ? "Outreach Error: " : "Success: "}</strong>
            {feedback.error || feedback.message || "Operation executed successfully."}
            {feedback.remaining_quota !== undefined && (
              <span style={{ marginLeft: "12px", opacity: 0.85 }}>
                (Remaining Daily Quota: {feedback.remaining_quota})
              </span>
            )}
          </div>
        </div>
      )}

      {/* Main Grid: JD & Outreach on Left, Settings/Results on Right */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: "24px", marginBottom: "32px" }}>
        {/* Left Column: Composer */}
        <div style={{ background: "#111827", padding: "24px", borderRadius: "12px", border: "1px solid #1f2937" }}>
          <h3 style={{ margin: "0 0 16px", fontSize: "1.1rem", display: "flex", alignItems: "center", gap: "8px" }}>
            <Sparkles size={18} color="#38bdf8" />
            Job Description to Outreach Composer
          </h3>

          {/* Recipients */}
          <div style={{ marginBottom: "14px" }}>
            <label style={{ display: "block", fontSize: "0.82rem", color: "#9ca3af", marginBottom: "4px" }}>
              Recipient Email(s) (comma, semicolon, or newline separated)
            </label>
            <input
              type="text"
              value={recipientsText}
              onChange={(e) => setRecipientsText(e.target.value)}
              placeholder="e.g. Sarah Connor <sarah@stripe.com>, hr@openai.com"
              style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box" }}
            />
          </div>

          {/* Job Description */}
          <div style={{ marginBottom: "14px" }}>
            <label style={{ display: "block", fontSize: "0.82rem", color: "#9ca3af", marginBottom: "4px" }}>
              Target Job Description (JD) / Company Context
            </label>
            <textarea
              rows={4}
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              placeholder="Paste target job post: e.g. We are looking for a Senior Python & GenAI Engineer with FastAPI and PostgreSQL experience..."
              style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box", fontFamily: "inherit" }}
            />
          </div>

          {/* Draft with AI Helping Hand Button */}
          <div style={{ marginBottom: "20px" }}>
            <button
              onClick={handleRunDraft}
              disabled={drafting}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                background: "linear-gradient(135deg, #0284c7 0%, #7c3aed 100%)",
                border: "none",
                color: "#ffffff",
                padding: "10px 20px",
                borderRadius: "8px",
                fontWeight: 700,
                fontSize: "0.88rem",
                cursor: drafting ? "not-allowed" : "pointer",
              }}
            >
              <Sparkles size={16} />
              {drafting ? "Analyzing JD & Drafting with AI..." : "Draft with AI Helping Hand"}
            </button>
          </div>

          {/* Subject Line */}
          <div style={{ marginBottom: "14px" }}>
            <label style={{ display: "block", fontSize: "0.82rem", color: "#9ca3af", marginBottom: "4px" }}>
              Email Subject Line
            </label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Subject line..."
              style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box" }}
            />
          </div>

          {/* Email Body */}
          <div style={{ marginBottom: "16px" }}>
            <label style={{ display: "block", fontSize: "0.82rem", color: "#9ca3af", marginBottom: "4px" }}>
              Email Body (Supports {"{name}"} and {"{company}"} placeholders)
            </label>
            <textarea
              rows={6}
              value={bodyText}
              onChange={(e) => setBodyText(e.target.value)}
              placeholder="Hi {name}, I'm reaching out regarding..."
              style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box", fontFamily: "inherit", fontSize: "0.88rem", lineHeight: "1.5" }}
            />
          </div>

          {/* Resume Attachment Option */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "24px", background: "rgba(15, 23, 42, 0.6)", padding: "10px 14px", borderRadius: "8px", border: "1px solid #1e293b" }}>
            <input
              type="checkbox"
              id="attachResumeCheck"
              checked={attachResume}
              onChange={(e) => setAttachResume(e.target.checked)}
              style={{ cursor: "pointer", width: "16px", height: "16px" }}
            />
            <label htmlFor="attachResumeCheck" style={{ fontSize: "0.85rem", color: "#e2e8f0", cursor: "pointer", display: "flex", alignItems: "center", gap: "8px" }}>
              <Paperclip size={16} color="#38bdf8" />
              Attach Active Resume
              {primaryAttachment ? (
                <span style={{ color: "#38bdf8", fontWeight: 600 }}>({primaryAttachment.filename})</span>
              ) : (
                <span style={{ color: "#94a3b8" }}>(Upload in Settings)</span>
              )}
            </label>
          </div>

          {/* Action Buttons */}
          <div style={{ display: "flex", gap: "14px", flexWrap: "wrap" }}>
            <button
              onClick={() => handleRunSend(true)}
              disabled={sending}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                background: "#22c55e",
                border: "none",
                color: "#111827",
                padding: "11px 22px",
                borderRadius: "8px",
                fontWeight: 700,
                fontSize: "0.9rem",
                cursor: sending ? "not-allowed" : "pointer",
              }}
            >
              <Send size={16} />
              {sending ? "Dispatching..." : "Send Now (Instant Egress)"}
            </button>

            <button
              onClick={() => handleRunSend(false)}
              disabled={sending}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                background: "#1e293b",
                border: "1px solid #475569",
                color: "#e2e8f0",
                padding: "11px 22px",
                borderRadius: "8px",
                fontWeight: 600,
                fontSize: "0.9rem",
                cursor: sending ? "not-allowed" : "pointer",
              }}
            >
              <Calendar size={16} />
              Schedule into 30/Day Batch
            </button>
          </div>
        </div>

        {/* Right Column: ATS Match Fit & BYOK Key */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* ATS Fit Card */}
          <div style={{ background: "#111827", padding: "20px", borderRadius: "12px", border: "1px solid #1f2937" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: "1.05rem", color: "#c084fc", display: "flex", alignItems: "center", gap: "8px" }}>
              <Zap size={18} />
              ATS Keyword & Fit Analysis
            </h3>

            {matchScore !== null ? (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <span style={{ fontSize: "0.85rem", color: "#9ca3af" }}>Profile Alignment:</span>
                  <span style={{ fontSize: "1.2rem", fontWeight: 800, color: matchScore >= 70 ? "#22c55e" : "#fbbf24" }}>
                    {matchScore}% Match
                  </span>
                </div>

                {matchedSkills.length > 0 && (
                  <div style={{ marginBottom: "12px" }}>
                    <div style={{ fontSize: "0.78rem", color: "#9ca3af", marginBottom: "6px" }}>Matched Overlapping Skills:</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                      {matchedSkills.map((s, idx) => (
                        <span key={idx} style={{ background: "rgba(34, 197, 94, 0.15)", color: "#4ade80", padding: "3px 8px", borderRadius: "4px", fontSize: "0.75rem", fontWeight: 600 }}>
                          ✓ {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {missingSkills.length > 0 && (
                  <div>
                    <div style={{ fontSize: "0.78rem", color: "#9ca3af", marginBottom: "6px" }}>JD Skills Not in Profile:</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                      {missingSkills.slice(0, 5).map((s, idx) => (
                        <span key={idx} style={{ background: "rgba(245, 158, 11, 0.15)", color: "#fbbf24", padding: "3px 8px", borderRadius: "4px", fontSize: "0.75rem" }}>
                          + {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div style={{ marginTop: "12px", fontSize: "0.76rem", color: "#64748b" }}>
                  Generated using: <strong>{providerUsed === "gemini" ? "Google Gemini BYOK" : "Smart Template Engine"}</strong>
                </div>
              </div>
            ) : (
              <div style={{ padding: "20px", textAlign: "center", color: "#64748b", fontSize: "0.85rem", border: "1px dashed #334155", borderRadius: "8px" }}>
                Paste a Job Description and click "Draft with AI" to see real-time ATS keyword matching and skills overlap.
              </div>
            )}
          </div>

          {/* Gemini BYOK Card */}
          <div style={{ background: "#111827", padding: "20px", borderRadius: "12px", border: "1px solid #1f2937" }}>
            <h3 style={{ margin: "0 0 10px", fontSize: "1.02rem", color: "#ffffff", display: "flex", alignItems: "center", gap: "8px" }}>
              <Key size={16} color="#38bdf8" />
              Gemini API Key (BYOK)
            </h3>
            <p style={{ margin: "0 0 12px", fontSize: "0.8rem", color: "#94a3b8" }}>
              Encrypted at rest using AES-256-GCM. Never logged or exposed.
            </p>

            {activeKey && (
              <div style={{ background: "rgba(15, 23, 42, 0.7)", border: "1px solid #1e293b", padding: "10px 12px", borderRadius: "6px", marginBottom: "12px", fontSize: "0.82rem", display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "#9ca3af" }}>Active: {activeKey.model}</span>
                <span style={{ color: "#38bdf8", fontWeight: 600 }}>{activeKey.masked_key}</span>
              </div>
            )}

            <div style={{ marginBottom: "10px" }}>
              <input
                type="password"
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                placeholder="AIzaSy... (Paste new key)"
                style={{ width: "100%", padding: "8px 10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box", fontSize: "0.85rem" }}
              />
            </div>
            <div style={{ display: "flex", gap: "10px" }}>
              <select
                value={keyModel}
                onChange={(e) => setKeyModel(e.target.value)}
                style={{ flex: 1, padding: "8px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", fontSize: "0.82rem" }}
              >
                <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
              </select>
              <button
                onClick={handleSaveKeySubmit}
                disabled={keySaving || !newKey.trim()}
                style={{
                  background: "#0284c7",
                  border: "none",
                  color: "#ffffff",
                  padding: "8px 14px",
                  borderRadius: "6px",
                  fontWeight: 600,
                  fontSize: "0.82rem",
                  cursor: keySaving || !newKey.trim() ? "not-allowed" : "pointer",
                }}
              >
                {keySaving ? "Saving..." : "Save Key"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

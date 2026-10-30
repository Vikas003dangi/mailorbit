"use client";

import React, { useState } from "react";
import {
  Key,
  Lock,
  User,
  Mail,
  ShieldAlert,
  Trash2,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Eye,
  EyeOff,
  Sun,
  Moon,
  Sparkles,
  BookOpen,
} from "lucide-react";
import DocumentLibrary from "./DocumentLibrary";
import HighLimitWarningModal from "./HighLimitWarningModal";

interface AccountSettingsProps {
  currentUser: any;
  token: string | null;
  apiUrl: string;
  theme: "dark" | "light";
  onToggleTheme: () => void;
  dailyCap: number;
  onUpdateDailyCap: (cap: number) => Promise<void>;
  relayEmail: string;
  relayScriptUrl: string;
  relayAuthToken: string;
  onChangeRelayEmail: (val: string) => void;
  onChangeRelayUrl: (val: string) => void;
  onChangeRelayToken: (val: string) => void;
  onSaveRelay: () => Promise<void>;
  relaySaving: boolean;
  attachments: any[];
  onUploadResume: (e: React.ChangeEvent<HTMLInputElement>) => Promise<void> | void;
  onDeleteResume: (id: string) => Promise<void> | void;
  uploadingResume?: boolean;
  onLogout: () => void;
  onOpenTutorial: (tab: any) => void;
  isDemoMode: boolean;
}

export default function AccountSettingsSection({
  currentUser,
  token,
  apiUrl,
  theme,
  onToggleTheme,
  dailyCap,
  onUpdateDailyCap,
  relayEmail,
  relayScriptUrl,
  relayAuthToken,
  onChangeRelayEmail,
  onChangeRelayUrl,
  onChangeRelayToken,
  onSaveRelay,
  relaySaving,
  attachments,
  onUploadResume,
  onDeleteResume,
  uploadingResume = false,
  onLogout,
  onOpenTutorial,
  isDemoMode,
}: AccountSettingsProps) {
  const isLight = theme === "light";

  // Card theme styling tokens
  const cardBg = isLight ? "#ffffff" : "#111827";
  const cardBorder = isLight ? "#e2e8f0" : "#1f2937";
  const textTitle = isLight ? "#0f172a" : "#f8fafc";
  const textMuted = isLight ? "#64748b" : "#94a3b8";
  const inputBg = isLight ? "#f8fafc" : "#1f2937";
  const inputBorder = isLight ? "#cbd5e1" : "#374151";

  // Daily limit slider & warning modal
  const [sliderCap, setSliderCap] = useState(dailyCap);
  const [pendingCap, setPendingCap] = useState<number | null>(null);
  const [warningModalOpen, setWarningModalOpen] = useState(false);

  // Profile editing
  const [senderName, setSenderName] = useState(currentUser?.sender_name || "");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileNotice, setProfileNotice] = useState<string | null>(null);

  // Password update states
  const [changePasswordStep, setChangePasswordStep] = useState<"initial" | "otp">("initial");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordOtp, setPasswordOtp] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordUpdating, setPasswordUpdating] = useState(false);
  const [passwordNotice, setPasswordNotice] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  // Account deletion states
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteOtpSent, setDeleteOtpSent] = useState(false);
  const [deleteOtp, setDeleteOtp] = useState("");
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [showDeletePassword, setShowDeletePassword] = useState(false);
  const [deletingAccount, setDeletingAccount] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Resume ATS scanning
  const [scanningResume, setScanningResume] = useState(false);
  const [scanResult, setScanResult] = useState<any>(null);

  const apiFetch = async (endpoint: string, options: RequestInit = {}) => {
    if (isDemoMode) {
      return { ok: true, json: async () => ({ status: "success", message: "Demo mode simulated" }) } as Response;
    }
    const headers = {
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
    };
    return fetch(`${apiUrl}${endpoint}`, { ...options, headers });
  };

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(e.target.value, 10);
    setSliderCap(val);
    if (val > 30) {
      setPendingCap(val);
      setWarningModalOpen(true);
    } else {
      onUpdateDailyCap(val);
    }
  };

  const handleConfirmHighLimit = async () => {
    if (pendingCap) {
      await onUpdateDailyCap(pendingCap);
      setWarningModalOpen(false);
      setPendingCap(null);
    }
  };

  const handleCancelHighLimit = () => {
    setSliderCap(30);
    onUpdateDailyCap(30);
    setWarningModalOpen(false);
    setPendingCap(null);
  };

  // 1. Save Sender Name Profile
  const handleSaveSenderName = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileSaving(true);
    setProfileNotice(null);
    try {
      const res = await apiFetch("/api/v1/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ full_name: senderName.trim() }),
      });
      if (res.ok) {
        setProfileNotice("Sender name updated successfully.");
      } else {
        setProfileNotice("Could not update profile name.");
      }
    } catch (err: any) {
      setProfileNotice(`Error: ${err.message}`);
    } finally {
      setProfileSaving(false);
    }
  };

  // 2. Request Password Change OTP
  const handleRequestPasswordOtp = async () => {
    setPasswordUpdating(true);
    setPasswordError(null);
    setPasswordNotice(null);
    try {
      const res = await apiFetch("/api/v1/auth/change-password-otp", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not dispatch code.");
      setChangePasswordStep("otp");
      setPasswordNotice("A 6-digit confirmation code was sent to your registered email.");
    } catch (err: any) {
      setPasswordError(err.message || "Failed to request code.");
    } finally {
      setPasswordUpdating(false);
    }
  };

  // 3. Confirm Password Change
  const handleConfirmPasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match.");
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters.");
      return;
    }
    if (passwordOtp.trim().length !== 6) {
      setPasswordError("Please enter the 6-digit code.");
      return;
    }

    setPasswordUpdating(true);
    setPasswordError(null);
    setPasswordNotice(null);
    try {
      const res = await apiFetch("/api/v1/auth/confirm-change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword,
          otp: passwordOtp.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not update password.");
      setPasswordNotice("Password updated successfully!");
      setChangePasswordStep("initial");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordOtp("");
    } catch (err: any) {
      setPasswordError(err.message || "Password update failed.");
    } finally {
      setPasswordUpdating(false);
    }
  };

  // 4. Request Account Deletion OTP
  const handleRequestDeleteOtp = async () => {
    setDeletingAccount(true);
    setDeleteError(null);
    try {
      const res = await apiFetch("/api/v1/auth/delete-account-otp", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not dispatch deletion code.");
      setDeleteOtpSent(true);
    } catch (err: any) {
      setDeleteError(err.message || "Failed to dispatch deletion code.");
    } finally {
      setDeletingAccount(false);
    }
  };

  // 5. Confirm Permanent Account Deletion
  const handleConfirmDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (deleteConfirmText.trim().toUpperCase() !== "DELETE") {
      setDeleteError("Please type DELETE to confirm.");
      return;
    }
    if (deleteOtp.trim().length !== 6) {
      setDeleteError("Please enter the 6-digit code.");
      return;
    }

    setDeletingAccount(true);
    setDeleteError(null);
    try {
      const res = await apiFetch("/api/v1/auth/confirm-delete-account", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          password: deletePassword,
          confirmation_text: "DELETE",
          otp: deleteOtp.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Account deletion failed.");
      alert("Workspace and account permanently deleted.");
      onLogout();
    } catch (err: any) {
      setDeleteError(err.message || "Failed to delete account.");
    } finally {
      setDeletingAccount(false);
    }
  };

  // 6. Trigger Resume ATS Scan
  const handleScanResume = async (attachmentId?: string) => {
    setScanningResume(true);
    try {
      const res = await apiFetch("/api/v1/ai/scan-resume", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ attachment_id: attachmentId || undefined }),
      });
      if (res.ok) {
        const data = await res.json();
        setScanResult(data);
      }
    } catch (err) {
      console.error("Resume scan error", err);
    } finally {
      setScanningResume(false);
    }
  };

  return (
    <div>
      {/* Header Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 800, color: textTitle, margin: "0 0 6px" }}>
            Workspace Settings, Security & Relay
          </h1>
          <p style={{ color: textMuted, fontSize: "0.92rem", margin: 0 }}>
            Manage identity, visual themes, Google Apps Script email relay, Cloudinary resumes, and account credentials.
          </p>
        </div>
        <button
          onClick={() => onOpenTutorial("relay")}
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
          📘 Setup Guide & Flowcharts
        </button>
      </div>

      {/* SECTION 1: IDENTITY & THEME */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "24px" }} className="responsive-2col">
        {/* Profile Card */}
        <div style={{ background: cardBg, padding: "22px", borderRadius: "12px", border: `1px solid ${cardBorder}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
            <User size={18} color="#38bdf8" />
            <h3 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 700, color: textTitle }}>Sender Identity & Workspace</h3>
          </div>
          <form onSubmit={handleSaveSenderName} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "4px" }}>
                Sender Full Name (Shown in outbound headers)
              </label>
              <input
                type="text"
                value={senderName}
                onChange={(e) => setSenderName(e.target.value)}
                placeholder="e.g. Vikas Dangi"
                style={{ width: "100%", padding: "10px", borderRadius: "6px", background: inputBg, border: `1px solid ${inputBorder}`, color: textTitle, boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "4px" }}>
                Registered Account Email
              </label>
              <input
                type="email"
                readOnly
                disabled
                value={currentUser?.email || ""}
                style={{ width: "100%", padding: "10px", borderRadius: "6px", background: isLight ? "#f1f5f9" : "#0f172a", border: `1px solid ${inputBorder}`, color: textMuted, boxSizing: "border-box" }}
              />
            </div>
            {profileNotice && (
              <div style={{ fontSize: "0.82rem", color: "#38bdf8" }}>{profileNotice}</div>
            )}
            <button
              type="submit"
              disabled={profileSaving}
              style={{ background: "#0284c7", color: "#ffffff", border: "none", padding: "10px", borderRadius: "6px", fontWeight: 600, cursor: profileSaving ? "not-allowed" : "pointer", alignSelf: "flex-start" }}
            >
              {profileSaving ? "Saving..." : "Save Identity"}
            </button>
          </form>
        </div>

        {/* Theme & Display Mode Card */}
        <div style={{ background: cardBg, padding: "22px", borderRadius: "12px", border: `1px solid ${cardBorder}`, display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
              {isLight ? <Sun size={18} color="#f59e0b" /> : <Moon size={18} color="#38bdf8" />}
              <h3 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 700, color: textTitle }}>Appearance & Theme</h3>
            </div>
            <p style={{ color: textMuted, fontSize: "0.84rem", margin: "0 0 16px" }}>
              Toggle between deep celestial dark mode and high-contrast light mode across all cards, modals, and tables.
            </p>
          </div>
          <div style={{ display: "flex", gap: "12px" }}>
            <button
              onClick={() => { if (theme !== "dark") onToggleTheme(); }}
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                padding: "12px",
                borderRadius: "8px",
                border: theme === "dark" ? "2px solid #0284c7" : `1px solid ${cardBorder}`,
                background: theme === "dark" ? "rgba(2, 132, 199, 0.2)" : "transparent",
                color: theme === "dark" ? "#38bdf8" : textMuted,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              <Moon size={16} /> Dark Nebula
            </button>
            <button
              onClick={() => { if (theme !== "light") onToggleTheme(); }}
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                padding: "12px",
                borderRadius: "8px",
                border: theme === "light" ? "2px solid #0284c7" : `1px solid ${cardBorder}`,
                background: theme === "light" ? "rgba(2, 132, 199, 0.15)" : "transparent",
                color: theme === "light" ? "#0284c7" : textMuted,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              <Sun size={16} /> Crisp Light
            </button>
          </div>
        </div>
      </div>

      {/* SECTION 2: DAILY CAP SLIDER WITH >30 MODAL */}
      <div style={{ background: cardBg, padding: "20px 24px", borderRadius: "12px", border: `1px solid ${cardBorder}`, marginBottom: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px", flexWrap: "wrap", gap: "10px" }}>
          <div>
            <h3 style={{ margin: "0 0 4px", fontSize: "1.05rem", fontWeight: 700, color: textTitle }}>
              Daily Sending Cap (Single Sender)
            </h3>
            <p style={{ margin: 0, fontSize: "0.82rem", color: textMuted }}>
              Fair-share water-filling distributes this capacity evenly across all active campaigns and sub-batches.
            </p>
          </div>
          <span
            style={{
              fontSize: "1.1rem",
              fontWeight: 800,
              color: sliderCap <= 30 ? "#38bdf8" : "#fbbf24",
              background: isLight ? "#f1f5f9" : "rgba(15, 23, 42, 0.8)",
              padding: "4px 12px",
              borderRadius: "6px",
              border: `1px solid ${cardBorder}`,
            }}
          >
            {sliderCap} emails / day
          </span>
        </div>

        <div style={{ marginTop: "12px", marginBottom: "8px" }}>
          <input
            type="range"
            min={5}
            max={100}
            step={5}
            value={sliderCap}
            onChange={handleSliderChange}
            style={{ width: "100%", accentColor: sliderCap <= 30 ? "#38bdf8" : "#f59e0b", cursor: "pointer" }}
          />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: textMuted }}>
          <span>5 / day (Ultra Safe)</span>
          <span style={{ color: "#38bdf8", fontWeight: 700 }}>30 / day (Default Gmail Deliverability Limit)</span>
          <span style={{ color: "#f59e0b" }}>100 / day (High Volume Warning)</span>
        </div>
      </div>

      {/* SECTION 3: APPS SCRIPT RELAY CONNECTION */}
      <div style={{ background: cardBg, padding: "24px", borderRadius: "12px", border: `1px solid ${cardBorder}`, marginBottom: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
          <div>
            <h3 style={{ margin: "0 0 4px", fontSize: "1.05rem", fontWeight: 700, color: textTitle }}>
              Google Apps Script Email Relay
            </h3>
            <p style={{ margin: 0, fontSize: "0.82rem", color: textMuted }}>
              Zero-password email dispatch through your personal Apps Script Web App. Stored token is encrypted with AES-256-GCM.
            </p>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "14px" }} className="responsive-2col">
          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "4px" }}>
              Sender Gmail Address
            </label>
            <input
              type="email"
              value={relayEmail}
              onChange={(e) => onChangeRelayEmail(e.target.value)}
              placeholder="you@gmail.com"
              style={{ width: "100%", padding: "10px", borderRadius: "6px", background: inputBg, border: `1px solid ${inputBorder}`, color: textTitle, boxSizing: "border-box" }}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "4px" }}>
              Relay Secret Token
            </label>
            <input
              type="password"
              value={relayAuthToken}
              onChange={(e) => onChangeRelayToken(e.target.value)}
              placeholder="Secret configured in Apps Script properties"
              style={{ width: "100%", padding: "10px", borderRadius: "6px", background: inputBg, border: `1px solid ${inputBorder}`, color: textTitle, boxSizing: "border-box" }}
            />
          </div>
        </div>

        <div style={{ marginBottom: "16px" }}>
          <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "4px" }}>
            Apps Script Web App URL
          </label>
          <input
            type="url"
            value={relayScriptUrl}
            onChange={(e) => onChangeRelayUrl(e.target.value)}
            placeholder="https://script.google.com/macros/s/.../exec"
            style={{ width: "100%", padding: "10px", borderRadius: "6px", background: inputBg, border: `1px solid ${inputBorder}`, color: textTitle, boxSizing: "border-box" }}
          />
        </div>

        <button
          onClick={onSaveRelay}
          disabled={relaySaving}
          style={{ background: "#0284c7", color: "#ffffff", border: "none", padding: "10px 20px", borderRadius: "6px", cursor: relaySaving ? "not-allowed" : "pointer", fontWeight: 700 }}
        >
          {relaySaving ? "Verifying & Connecting..." : "Save Relay Configuration"}
        </button>
      </div>

      {/* SECTION 4: DOCUMENT LIBRARY & RESUME SCANNER */}
      <div style={{ marginBottom: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", flexWrap: "wrap", gap: "10px" }}>
          <h3 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 700, color: textTitle }}>
            Multi-Resume Document Library ({attachments.length})
          </h3>
          {attachments.length > 0 && (
            <button
              onClick={() => handleScanResume(attachments[0]?.id)}
              disabled={scanningResume}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                background: "linear-gradient(135deg, #0284c7 0%, #6366f1 100%)",
                color: "#ffffff",
                border: "none",
                padding: "8px 14px",
                borderRadius: "6px",
                fontWeight: 700,
                fontSize: "0.82rem",
                cursor: scanningResume ? "not-allowed" : "pointer",
              }}
            >
              <Sparkles size={14} />
              {scanningResume ? "Scanning Resume..." : "Scan Resume & Generate ATS Templates"}
            </button>
          )}
        </div>

        {scanResult && (
          <div style={{ background: isLight ? "#f0fdf4" : "rgba(34, 197, 94, 0.1)", border: "1px solid #22c55e", padding: "16px", borderRadius: "10px", marginBottom: "16px" }}>
            <h4 style={{ margin: "0 0 8px", color: "#22c55e", fontSize: "0.95rem" }}>
              ✅ Resume Scanned: {scanResult.candidate_name} (Estimated ATS Score: {scanResult.ats_score_estimate}%)
            </h4>
            <div style={{ fontSize: "0.82rem", color: textMuted, marginBottom: "8px" }}>
              <strong>Extracted Skills:</strong> {scanResult.skills?.join(", ")}
            </div>
            <div style={{ fontSize: "0.8rem", color: textMuted }}>
              Generated 3 tailored templates: <em>Direct Application</em>, <em>Referral Pitch</em>, and <em>Founder Reachout</em> ready in AI Copilot!
            </div>
          </div>
        )}

        <DocumentLibrary
          attachments={attachments}
          onUpload={onUploadResume}
          onDelete={onDeleteResume}
          uploading={uploadingResume}
        />
      </div>

      {/* SECTION 5: UPDATE PASSWORD VIA OTP */}
      <div style={{ background: cardBg, padding: "24px", borderRadius: "12px", border: `1px solid ${cardBorder}`, marginBottom: "24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
          <Lock size={18} color="#38bdf8" />
          <h3 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 700, color: textTitle }}>Update Workspace Password</h3>
        </div>
        <p style={{ color: textMuted, fontSize: "0.84rem", margin: "0 0 16px" }}>
          Requires a single-use 6-digit confirmation code dispatched to your registered email address.
        </p>

        {passwordNotice && (
          <div style={{ background: "rgba(34, 197, 94, 0.12)", border: "1px solid #22c55e", color: "#4ade80", padding: "10px 14px", borderRadius: "8px", marginBottom: "14px", fontSize: "0.84rem" }}>
            {passwordNotice}
          </div>
        )}

        {passwordError && (
          <div style={{ background: "rgba(239, 68, 68, 0.12)", border: "1px solid #ef4444", color: "#fca5a5", padding: "10px 14px", borderRadius: "8px", marginBottom: "14px", fontSize: "0.84rem" }}>
            {passwordError}
          </div>
        )}

        {changePasswordStep === "initial" ? (
          <button
            onClick={handleRequestPasswordOtp}
            disabled={passwordUpdating}
            style={{
              background: "#1e293b",
              color: "#38bdf8",
              border: "1px solid #0284c7",
              padding: "10px 18px",
              borderRadius: "6px",
              fontWeight: 700,
              fontSize: "0.85rem",
              cursor: passwordUpdating ? "not-allowed" : "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            {passwordUpdating && <RefreshCw size={14} className="animate-spin" />}
            Request 6-Digit Password Change Code
          </button>
        ) : (
          <form onSubmit={handleConfirmPasswordChange} style={{ display: "flex", flexDirection: "column", gap: "14px", maxWidth: "440px" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "4px" }}>
                6-Digit Confirmation Code
              </label>
              <input
                type="text"
                required
                maxLength={6}
                value={passwordOtp}
                onChange={(e) => setPasswordOtp(e.target.value.replace(/\D/g, ""))}
                placeholder="123456"
                style={{ width: "100%", padding: "10px", borderRadius: "6px", background: inputBg, border: "2px solid #0284c7", color: "#38bdf8", fontSize: "1.1rem", letterSpacing: "4px", textAlign: "center", fontWeight: 800, boxSizing: "border-box" }}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "4px" }}>
                Current Password
              </label>
              <div style={{ position: "relative" }}>
                <input
                  type={showCurrentPassword ? "text" : "password"}
                  required
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="••••••••••••"
                  style={{ width: "100%", padding: "10px 38px 10px 12px", borderRadius: "6px", background: inputBg, border: `1px solid ${inputBorder}`, color: textTitle, boxSizing: "border-box" }}
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  style={{ position: "absolute", right: "10px", top: "50%", transform: "translateY(-50%)", background: "transparent", border: "none", color: textMuted, cursor: "pointer", padding: 0 }}
                >
                  {showCurrentPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "4px" }}>
                New Password (Min 8 characters)
              </label>
              <div style={{ position: "relative" }}>
                <input
                  type={showNewPassword ? "text" : "password"}
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••••••"
                  style={{ width: "100%", padding: "10px 38px 10px 12px", borderRadius: "6px", background: inputBg, border: `1px solid ${inputBorder}`, color: textTitle, boxSizing: "border-box" }}
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  style={{ position: "absolute", right: "10px", top: "50%", transform: "translateY(-50%)", background: "transparent", border: "none", color: textMuted, cursor: "pointer", padding: 0 }}
                >
                  {showNewPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "4px" }}>
                Confirm New Password
              </label>
              <div style={{ position: "relative" }}>
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  required
                  minLength={8}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••••••"
                  style={{ width: "100%", padding: "10px 38px 10px 12px", borderRadius: "6px", background: inputBg, border: `1px solid ${inputBorder}`, color: textTitle, boxSizing: "border-box" }}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  style={{ position: "absolute", right: "10px", top: "50%", transform: "translateY(-50%)", background: "transparent", border: "none", color: textMuted, cursor: "pointer", padding: 0 }}
                >
                  {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div style={{ display: "flex", gap: "10px", marginTop: "6px" }}>
              <button
                type="submit"
                disabled={passwordUpdating}
                style={{ background: "#0284c7", color: "#ffffff", border: "none", padding: "10px 18px", borderRadius: "6px", fontWeight: 700, cursor: passwordUpdating ? "not-allowed" : "pointer" }}
              >
                {passwordUpdating ? "Updating..." : "Update Password"}
              </button>
              <button
                type="button"
                onClick={() => setChangePasswordStep("initial")}
                style={{ background: "transparent", color: textMuted, border: `1px solid ${cardBorder}`, padding: "10px 14px", borderRadius: "6px", cursor: "pointer" }}
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>

      {/* SECTION 6: DANGER ZONE: DELETE ACCOUNT */}
      <div style={{ background: isLight ? "#fef2f2" : "rgba(239, 68, 68, 0.05)", padding: "24px", borderRadius: "12px", border: "1px solid #ef4444" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
          <ShieldAlert size={20} color="#ef4444" />
          <h3 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 700, color: "#ef4444" }}>
            Danger Zone: Delete Workspace & Erase Data
          </h3>
        </div>
        <p style={{ color: isLight ? "#991b1b" : "#fca5a5", fontSize: "0.85rem", margin: "0 0 16px" }}>
          Permanently delete this account, all campaigns, contacts, relays, and uploaded resumes. This action cannot be undone.
        </p>

        {!deleteModalOpen ? (
          <button
            onClick={() => setDeleteModalOpen(true)}
            style={{
              background: "#ef4444",
              color: "#ffffff",
              border: "none",
              padding: "10px 18px",
              borderRadius: "6px",
              fontWeight: 700,
              fontSize: "0.85rem",
              cursor: "pointer",
            }}
          >
            Permanently Delete My Workspace
          </button>
        ) : (
          <div style={{ background: cardBg, padding: "20px", borderRadius: "10px", border: "1px solid #ef4444", maxWidth: "460px" }}>
            <h4 style={{ margin: "0 0 10px", color: "#ef4444", fontSize: "0.95rem" }}>
              Confirm Workspace Deletion
            </h4>

            {deleteError && (
              <div style={{ background: "rgba(239, 68, 68, 0.15)", border: "1px solid #ef4444", color: "#fca5a5", padding: "8px 12px", borderRadius: "6px", marginBottom: "12px", fontSize: "0.82rem" }}>
                {deleteError}
              </div>
            )}

            {!deleteOtpSent ? (
              <div>
                <p style={{ fontSize: "0.82rem", color: textMuted, margin: "0 0 14px" }}>
                  For security, we will dispatch a 6-digit confirmation code to <strong>{currentUser?.email}</strong>.
                </p>
                <div style={{ display: "flex", gap: "10px" }}>
                  <button
                    onClick={handleRequestDeleteOtp}
                    disabled={deletingAccount}
                    style={{ background: "#ef4444", color: "#ffffff", border: "none", padding: "9px 16px", borderRadius: "6px", fontWeight: 700, cursor: deletingAccount ? "not-allowed" : "pointer" }}
                  >
                    {deletingAccount ? "Sending Code..." : "Send Deletion Code"}
                  </button>
                  <button
                    onClick={() => setDeleteModalOpen(false)}
                    style={{ background: "transparent", color: textMuted, border: `1px solid ${cardBorder}`, padding: "9px 14px", borderRadius: "6px", cursor: "pointer" }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleConfirmDeleteAccount} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.8rem", color: textMuted, marginBottom: "4px" }}>
                    6-Digit Deletion Code
                  </label>
                  <input
                    type="text"
                    required
                    maxLength={6}
                    value={deleteOtp}
                    onChange={(e) => setDeleteOtp(e.target.value.replace(/\D/g, ""))}
                    placeholder="123456"
                    style={{ width: "100%", padding: "10px", borderRadius: "6px", background: inputBg, border: "2px solid #ef4444", color: "#ef4444", fontSize: "1.1rem", letterSpacing: "4px", textAlign: "center", fontWeight: 800, boxSizing: "border-box" }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.8rem", color: textMuted, marginBottom: "4px" }}>
                    Your Account Password
                  </label>
                  <div style={{ position: "relative" }}>
                    <input
                      type={showDeletePassword ? "text" : "password"}
                      required
                      value={deletePassword}
                      onChange={(e) => setDeletePassword(e.target.value)}
                      placeholder="••••••••••••"
                      style={{ width: "100%", padding: "10px 38px 10px 12px", borderRadius: "6px", background: inputBg, border: `1px solid ${inputBorder}`, color: textTitle, boxSizing: "border-box" }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowDeletePassword(!showDeletePassword)}
                      style={{ position: "absolute", right: "10px", top: "50%", transform: "translateY(-50%)", background: "transparent", border: "none", color: textMuted, cursor: "pointer", padding: 0 }}
                    >
                      {showDeletePassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.8rem", color: textMuted, marginBottom: "4px" }}>
                    Type <strong>DELETE</strong> to confirm
                  </label>
                  <input
                    type="text"
                    required
                    value={deleteConfirmText}
                    onChange={(e) => setDeleteConfirmText(e.target.value)}
                    placeholder="DELETE"
                    style={{ width: "100%", padding: "10px", borderRadius: "6px", background: inputBg, border: `1px solid ${inputBorder}`, color: textTitle, boxSizing: "border-box" }}
                  />
                </div>

                <div style={{ display: "flex", gap: "10px", marginTop: "6px" }}>
                  <button
                    type="submit"
                    disabled={deletingAccount}
                    style={{ background: "#ef4444", color: "#ffffff", border: "none", padding: "10px 18px", borderRadius: "6px", fontWeight: 700, cursor: deletingAccount ? "not-allowed" : "pointer" }}
                  >
                    {deletingAccount ? "Erasing..." : "Permanently Erase All Data"}
                  </button>
                  <button
                    type="button"
                    onClick={() => { setDeleteModalOpen(false); setDeleteOtpSent(false); }}
                    style={{ background: "transparent", color: textMuted, border: `1px solid ${cardBorder}`, padding: "10px 14px", borderRadius: "6px", cursor: "pointer" }}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </div>

      {/* High Limit Modal (>30) */}
      <HighLimitWarningModal
        isOpen={warningModalOpen}
        limit={pendingCap || 30}
        onConfirm={handleConfirmHighLimit}
        onCancel={handleCancelHighLimit}
      />
    </div>
  );
}

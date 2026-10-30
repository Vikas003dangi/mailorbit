"use client";

import React, { useState } from "react";
import {
  Mail,
  Lock,
  User,
  Eye,
  EyeOff,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  KeyRound,
  Zap,
} from "lucide-react";

interface AuthCardProps {
  apiUrl: string;
  onAuthSuccess: (token: string, user: any) => void;
  onLaunchDemo: () => void;
  theme?: "dark" | "light";
  superuserEmails?: string[];
}

export default function AuthCard({
  apiUrl,
  onAuthSuccess,
  onLaunchDemo,
  theme = "dark",
  superuserEmails = [],
}: AuthCardProps) {
  const isLight = theme === "light";

  const [authMode, setAuthMode] = useState<"login" | "signup" | "forgot">("login");
  const [signupStep, setSignupStep] = useState<"info" | "otp">("info");
  const [forgotStep, setForgotStep] = useState<"email" | "otp">("email");

  // Input states
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [otp, setOtp] = useState("");

  // Visibility toggles
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Status & loading
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  // Styling tokens
  const cardBg = isLight ? "#ffffff" : "#111827";
  const cardBorder = isLight ? "#e2e8f0" : "#1f2937";
  const textColor = isLight ? "#0f172a" : "#f8fafc";
  const textMuted = isLight ? "#64748b" : "#94a3b8";
  const inputBg = isLight ? "#f8fafc" : "#1f2937";
  const inputBorder = isLight ? "#cbd5e1" : "#374151";

  // 1. Handle Standard Login
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccessNotice(null);

    try {
      const res = await fetch(`${apiUrl}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Invalid email or password.");
      }
      onAuthSuccess(data.access_token, data.user);
    } catch (err: any) {
      setError(err.message || "Login failed.");
    } finally {
      setLoading(false);
    }
  };

  // 2. Handle Signup Step 1: Request 6-digit OTP
  const handleRequestSignupOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    setError(null);
    setSuccessNotice(null);

    try {
      const res = await fetch(`${apiUrl}/api/v1/auth/signup-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), name: name.trim() || undefined }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Could not dispatch verification code.");
      }
      setSuccessNotice(data.message || `A 6-digit code was sent to ${email}.`);
      setSignupStep("otp");
    } catch (err: any) {
      setError(err.message || "Failed to dispatch verification code.");
    } finally {
      setLoading(false);
    }
  };

  // 3. Handle Signup Step 2: Verify OTP & Create Verified User
  const handleVerifySignupOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (otp.trim().length !== 6) {
      setError("Please enter the 6-digit verification code.");
      return;
    }

    setLoading(true);
    setError(null);
    setSuccessNotice(null);

    try {
      const res = await fetch(`${apiUrl}/api/v1/auth/verify-signup-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          otp: otp.trim(),
          password,
          confirm_password: confirmPassword,
          name: name.trim() || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Verification failed.");
      }
      onAuthSuccess(data.access_token, data.user);
    } catch (err: any) {
      setError(err.message || "Failed to create account.");
    } finally {
      setLoading(false);
    }
  };

  // 4. Handle Forgot Password Step 1: Request Reset OTP
  const handleRequestForgotOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    setError(null);
    setSuccessNotice(null);

    try {
      const res = await fetch(`${apiUrl}/api/v1/auth/forgot-password-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      const data = await res.json();
      setSuccessNotice(data.message || `If an account exists, a 6-digit code has been sent.`);
      setForgotStep("otp");
    } catch (err: any) {
      setError(err.message || "Request failed.");
    } finally {
      setLoading(false);
    }
  };

  // 5. Handle Forgot Password Step 2: Reset Password with OTP
  const handleResetPasswordWithOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (otp.trim().length !== 6) {
      setError("Please enter the 6-digit reset code.");
      return;
    }

    setLoading(true);
    setError(null);
    setSuccessNotice(null);

    try {
      const res = await fetch(`${apiUrl}/api/v1/auth/reset-password-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          otp: otp.trim(),
          new_password: password,
          confirm_password: confirmPassword,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Password reset failed.");
      }
      setSuccessNotice("Password updated successfully! You may now sign in.");
      setAuthMode("login");
      setForgotStep("email");
      setPassword("");
      setConfirmPassword("");
      setOtp("");
    } catch (err: any) {
      setError(err.message || "Failed to reset password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        maxWidth: "460px",
        margin: "40px auto",
        background: cardBg,
        padding: "36px 32px",
        borderRadius: "16px",
        border: `1px solid ${cardBorder}`,
        boxShadow: isLight
          ? "0 20px 45px rgba(0,0,0,0.06), 0 2px 10px rgba(0,0,0,0.04)"
          : "0 25px 60px rgba(0,0,0,0.7), 0 0 30px rgba(56, 189, 248, 0.08)",
      }}
    >
      {/* Brand Header */}
      <div style={{ textAlign: "center", marginBottom: "24px" }}>
        <h2 style={{ fontSize: "1.5rem", fontWeight: 800, color: textColor, margin: "0 0 6px" }}>
          {authMode === "login"
            ? "Welcome to MailOrbit"
            : authMode === "signup"
            ? "Create Verified Workspace"
            : "Reset Workspace Password"}
        </h2>
        <p style={{ color: textMuted, fontSize: "0.85rem", margin: 0 }}>
          {authMode === "login"
            ? "Autonomous cold outreach with 30/day fair-share water-filling."
            : authMode === "signup"
            ? "Strict email verification with secure single-use 6-digit code."
            : "Verify registered email to set a fresh secure password."}
        </p>
      </div>

      {/* Tabs Header (Log In vs Sign Up) */}
      {authMode !== "forgot" ? (
        <div style={{ display: "flex", borderBottom: `1px solid ${cardBorder}`, marginBottom: "22px" }}>
          <button
            type="button"
            onClick={() => {
              setAuthMode("login");
              setError(null);
              setSuccessNotice(null);
            }}
            style={{
              flex: 1,
              padding: "10px",
              background: "transparent",
              border: "none",
              borderBottom: authMode === "login" ? "2px solid #0284c7" : "none",
              color: authMode === "login" ? "#38bdf8" : textMuted,
              fontWeight: 700,
              fontSize: "0.9rem",
              cursor: "pointer",
            }}
          >
            Log In
          </button>
          <button
            type="button"
            onClick={() => {
              setAuthMode("signup");
              setSignupStep("info");
              setError(null);
              setSuccessNotice(null);
            }}
            style={{
              flex: 1,
              padding: "10px",
              background: "transparent",
              border: "none",
              borderBottom: authMode === "signup" ? "2px solid #0284c7" : "none",
              color: authMode === "signup" ? "#38bdf8" : textMuted,
              fontWeight: 700,
              fontSize: "0.9rem",
              cursor: "pointer",
            }}
          >
            Sign Up
          </button>
        </div>
      ) : (
        <div style={{ marginBottom: "18px" }}>
          <button
            type="button"
            onClick={() => {
              setAuthMode("login");
              setError(null);
              setSuccessNotice(null);
            }}
            style={{
              background: "transparent",
              border: "none",
              color: "#38bdf8",
              fontSize: "0.82rem",
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              gap: "6px",
              cursor: "pointer",
              padding: 0,
            }}
          >
            <ArrowLeft size={14} /> Back to Log In
          </button>
        </div>
      )}

      {/* Success Notice Banner */}
      {successNotice && (
        <div
          style={{
            background: "rgba(34, 197, 94, 0.12)",
            border: "1px solid #22c55e",
            color: "#4ade80",
            padding: "11px 14px",
            borderRadius: "8px",
            marginBottom: "16px",
            fontSize: "0.84rem",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <CheckCircle2 size={16} color="#22c55e" style={{ flexShrink: 0 }} />
          <div>{successNotice}</div>
        </div>
      )}

      {/* Error Notice Banner */}
      {error && (
        <div
          style={{
            background: "rgba(239, 68, 68, 0.12)",
            border: "1px solid #ef4444",
            color: "#fca5a5",
            padding: "11px 14px",
            borderRadius: "8px",
            marginBottom: "16px",
            fontSize: "0.84rem",
            display: "flex",
            alignItems: "flex-start",
            gap: "8px",
          }}
        >
          <AlertCircle size={16} color="#ef4444" style={{ flexShrink: 0, marginTop: "2px" }} />
          <div>{error}</div>
        </div>
      )}

      {/* ---------------- FORM: LOG IN ---------------- */}
      {authMode === "login" && (
        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "6px" }}>
              Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              style={{
                width: "100%",
                padding: "11px 14px",
                borderRadius: "8px",
                background: inputBg,
                border: `1px solid ${inputBorder}`,
                color: textColor,
                fontSize: "0.9rem",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <label style={{ fontSize: "0.82rem", color: textMuted }}>Password</label>
              <button
                type="button"
                onClick={() => {
                  setAuthMode("forgot");
                  setForgotStep("email");
                  setError(null);
                  setSuccessNotice(null);
                }}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#38bdf8",
                  fontSize: "0.78rem",
                  cursor: "pointer",
                  padding: 0,
                }}
              >
                Forgot Password?
              </button>
            </div>
            <div style={{ position: "relative" }}>
              <input
                type={showPassword ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                style={{
                  width: "100%",
                  padding: "11px 40px 11px 14px",
                  borderRadius: "8px",
                  background: inputBg,
                  border: `1px solid ${inputBorder}`,
                  color: textColor,
                  fontSize: "0.9rem",
                  boxSizing: "border-box",
                }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                style={{
                  position: "absolute",
                  right: "12px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "transparent",
                  border: "none",
                  color: textMuted,
                  cursor: "pointer",
                  padding: 0,
                  display: "flex",
                  alignItems: "center",
                }}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              background: loading ? "#0369a1" : "linear-gradient(135deg, #0284c7 0%, #2563eb 100%)",
              color: "#ffffff",
              border: "none",
              padding: "12px",
              borderRadius: "8px",
              fontWeight: 700,
              fontSize: "0.95rem",
              cursor: loading ? "not-allowed" : "pointer",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              gap: "8px",
              marginTop: "4px",
            }}
          >
            {loading && <RefreshCw size={16} className="animate-spin" />}
            {loading ? "Authenticating..." : "Sign In to Workspace"}
          </button>
        </form>
      )}

      {/* ---------------- FORM: SIGN UP (STEP 1: INFO) ---------------- */}
      {authMode === "signup" && signupStep === "info" && (
        <form onSubmit={handleRequestSignupOtp} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "6px" }}>
              Your Full Name <span style={{ fontSize: "0.75rem", color: textMuted }}>(Optional, shown on outbound emails)</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Vikas Dangi"
              style={{
                width: "100%",
                padding: "11px 14px",
                borderRadius: "8px",
                background: inputBg,
                border: `1px solid ${inputBorder}`,
                color: textColor,
                fontSize: "0.9rem",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "6px" }}>
              Work or Personal Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              style={{
                width: "100%",
                padding: "11px 14px",
                borderRadius: "8px",
                background: inputBg,
                border: `1px solid ${inputBorder}`,
                color: textColor,
                fontSize: "0.9rem",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div style={{ background: "rgba(56, 189, 248, 0.08)", border: "1px solid rgba(56, 189, 248, 0.25)", padding: "10px 14px", borderRadius: "8px", fontSize: "0.8rem", color: "#38bdf8" }}>
            🔒 We will send a 6-digit one-time verification code to this address to confirm ownership before workspace setup.
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              background: loading ? "#0369a1" : "linear-gradient(135deg, #0284c7 0%, #2563eb 100%)",
              color: "#ffffff",
              border: "none",
              padding: "12px",
              borderRadius: "8px",
              fontWeight: 700,
              fontSize: "0.95rem",
              cursor: loading ? "not-allowed" : "pointer",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              gap: "8px",
            }}
          >
            {loading && <RefreshCw size={16} className="animate-spin" />}
            {loading ? "Sending Code..." : "Send Verification Code"}
            {!loading && <ArrowRight size={16} />}
          </button>
        </form>
      )}

      {/* ---------------- FORM: SIGN UP (STEP 2: OTP & PASSWORDS) ---------------- */}
      {authMode === "signup" && signupStep === "otp" && (
        <form onSubmit={handleVerifySignupOtp} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <label style={{ fontSize: "0.82rem", color: textMuted }}>6-Digit Verification Code</label>
              <button
                type="button"
                onClick={() => setSignupStep("info")}
                style={{ background: "transparent", border: "none", color: "#38bdf8", fontSize: "0.78rem", cursor: "pointer", padding: 0 }}
              >
                Change Email
              </button>
            </div>
            <input
              type="text"
              required
              maxLength={6}
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
              placeholder="123456"
              style={{
                width: "100%",
                padding: "12px 14px",
                borderRadius: "8px",
                background: inputBg,
                border: "2px solid #0284c7",
                color: "#38bdf8",
                fontSize: "1.25rem",
                letterSpacing: "6px",
                textAlign: "center",
                fontWeight: 800,
                boxSizing: "border-box",
                fontFamily: "monospace",
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "6px" }}>
              Create Password (Min 8 characters)
            </label>
            <div style={{ position: "relative" }}>
              <input
                type={showPassword ? "text" : "password"}
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                style={{
                  width: "100%",
                  padding: "11px 40px 11px 14px",
                  borderRadius: "8px",
                  background: inputBg,
                  border: `1px solid ${inputBorder}`,
                  color: textColor,
                  fontSize: "0.9rem",
                  boxSizing: "border-box",
                }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: "absolute",
                  right: "12px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "transparent",
                  border: "none",
                  color: textMuted,
                  cursor: "pointer",
                  padding: 0,
                  display: "flex",
                }}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "6px" }}>
              Confirm Password
            </label>
            <div style={{ position: "relative" }}>
              <input
                type={showConfirmPassword ? "text" : "password"}
                required
                minLength={8}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••••••"
                style={{
                  width: "100%",
                  padding: "11px 40px 11px 14px",
                  borderRadius: "8px",
                  background: inputBg,
                  border: `1px solid ${inputBorder}`,
                  color: textColor,
                  fontSize: "0.9rem",
                  boxSizing: "border-box",
                }}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                style={{
                  position: "absolute",
                  right: "12px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "transparent",
                  border: "none",
                  color: textMuted,
                  cursor: "pointer",
                  padding: 0,
                  display: "flex",
                }}
              >
                {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              background: loading ? "#0369a1" : "linear-gradient(135deg, #0284c7 0%, #2563eb 100%)",
              color: "#ffffff",
              border: "none",
              padding: "12px",
              borderRadius: "8px",
              fontWeight: 700,
              fontSize: "0.95rem",
              cursor: loading ? "not-allowed" : "pointer",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              gap: "8px",
            }}
          >
            {loading && <RefreshCw size={16} className="animate-spin" />}
            {loading ? "Verifying..." : "Verify Code & Launch Workspace"}
          </button>
        </form>
      )}

      {/* ---------------- FORM: FORGOT PASSWORD ---------------- */}
      {authMode === "forgot" && forgotStep === "email" && (
        <form onSubmit={handleRequestForgotOtp} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "6px" }}>
              Registered Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              style={{
                width: "100%",
                padding: "11px 14px",
                borderRadius: "8px",
                background: inputBg,
                border: `1px solid ${inputBorder}`,
                color: textColor,
                fontSize: "0.9rem",
                boxSizing: "border-box",
              }}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              background: loading ? "#0369a1" : "linear-gradient(135deg, #0284c7 0%, #2563eb 100%)",
              color: "#ffffff",
              border: "none",
              padding: "12px",
              borderRadius: "8px",
              fontWeight: 700,
              fontSize: "0.95rem",
              cursor: loading ? "not-allowed" : "pointer",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              gap: "8px",
            }}
          >
            {loading && <RefreshCw size={16} className="animate-spin" />}
            {loading ? "Sending Code..." : "Send Reset Code"}
            {!loading && <ArrowRight size={16} />}
          </button>
        </form>
      )}

      {authMode === "forgot" && forgotStep === "otp" && (
        <form onSubmit={handleResetPasswordWithOtp} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "6px" }}>
              6-Digit Reset Code
            </label>
            <input
              type="text"
              required
              maxLength={6}
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
              placeholder="123456"
              style={{
                width: "100%",
                padding: "12px 14px",
                borderRadius: "8px",
                background: inputBg,
                border: "2px solid #0284c7",
                color: "#38bdf8",
                fontSize: "1.25rem",
                letterSpacing: "6px",
                textAlign: "center",
                fontWeight: 800,
                boxSizing: "border-box",
                fontFamily: "monospace",
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "6px" }}>
              New Password (Min 8 characters)
            </label>
            <div style={{ position: "relative" }}>
              <input
                type={showPassword ? "text" : "password"}
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                style={{
                  width: "100%",
                  padding: "11px 40px 11px 14px",
                  borderRadius: "8px",
                  background: inputBg,
                  border: `1px solid ${inputBorder}`,
                  color: textColor,
                  fontSize: "0.9rem",
                  boxSizing: "border-box",
                }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: "absolute",
                  right: "12px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "transparent",
                  border: "none",
                  color: textMuted,
                  cursor: "pointer",
                  padding: 0,
                  display: "flex",
                }}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.82rem", color: textMuted, marginBottom: "6px" }}>
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
                style={{
                  width: "100%",
                  padding: "11px 40px 11px 14px",
                  borderRadius: "8px",
                  background: inputBg,
                  border: `1px solid ${inputBorder}`,
                  color: textColor,
                  fontSize: "0.9rem",
                  boxSizing: "border-box",
                }}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                style={{
                  position: "absolute",
                  right: "12px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "transparent",
                  border: "none",
                  color: textMuted,
                  cursor: "pointer",
                  padding: 0,
                  display: "flex",
                }}
              >
                {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              background: loading ? "#0369a1" : "linear-gradient(135deg, #0284c7 0%, #2563eb 100%)",
              color: "#ffffff",
              border: "none",
              padding: "12px",
              borderRadius: "8px",
              fontWeight: 700,
              fontSize: "0.95rem",
              cursor: loading ? "not-allowed" : "pointer",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              gap: "8px",
            }}
          >
            {loading && <RefreshCw size={16} className="animate-spin" />}
            {loading ? "Updating Password..." : "Reset Password & Sign In"}
          </button>
        </form>
      )}

      {/* Sandbox Demo Button */}
      <div style={{ marginTop: "24px", paddingTop: "20px", borderTop: `1px solid ${cardBorder}`, textAlign: "center" }}>
        <p style={{ fontSize: "0.82rem", color: textMuted, marginBottom: "12px" }}>
          Want to explore without creating an account?
        </p>
        <button
          onClick={onLaunchDemo}
          style={{
            width: "100%",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: "8px",
            background: isLight ? "#e0f2fe" : "#1e293b",
            color: "#0284c7",
            border: "1px solid #0284c7",
            padding: "11px",
            borderRadius: "8px",
            fontWeight: 700,
            fontSize: "0.86rem",
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
        >
          <Zap size={14} color="#0284c7" />
          ⚡ Launch Interactive Sandbox (Demo Mode)
        </button>
      </div>
    </div>
  );
}

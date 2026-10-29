"use client";

import React from "react";
import { AlertCircle, ShieldAlert, X, Check } from "lucide-react";

interface HighLimitWarningModalProps {
  isOpen: boolean;
  limit: number;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function HighLimitWarningModal({
  isOpen,
  limit,
  onConfirm,
  onCancel,
}: HighLimitWarningModalProps) {
  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "16px",
      }}
    >
      <div
        style={{
          background: "#111827",
          border: "1px solid #f59e0b",
          borderRadius: "14px",
          maxWidth: "520px",
          width: "100%",
          padding: "26px",
          boxShadow: "0 20px 40px rgba(0, 0, 0, 0.6), 0 0 20px rgba(245, 158, 11, 0.2)",
          color: "#f3f4f6",
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", gap: "14px", marginBottom: "18px" }}>
          <div
            style={{
              background: "rgba(245, 158, 11, 0.15)",
              border: "1px solid #f59e0b",
              borderRadius: "10px",
              padding: "10px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <ShieldAlert size={28} color="#fbbf24" />
          </div>
          <div>
            <h3 style={{ margin: "0 0 6px", fontSize: "1.22rem", fontWeight: 700, color: "#fbbf24" }}>
              High Daily Sending Limit Warning
            </h3>
            <p style={{ margin: 0, fontSize: "0.88rem", color: "#9ca3af" }}>
              You are increasing the sender daily cap to <strong>{limit} emails/day</strong>.
            </p>
          </div>
        </div>

        <div
          style={{
            background: "rgba(15, 23, 42, 0.75)",
            border: "1px solid #334155",
            borderRadius: "8px",
            padding: "14px 16px",
            fontSize: "0.85rem",
            lineHeight: "1.55",
            color: "#cbd5e1",
            marginBottom: "20px",
          }}
        >
          <div style={{ display: "flex", alignItems: "flex-start", gap: "8px", marginBottom: "10px" }}>
            <AlertCircle size={16} color="#fbbf24" style={{ flexShrink: 0, marginTop: "2px" }} />
            <div>
              <strong>Personal Gmail Quota Risk:</strong> Google Apps Script enforces a rolling 24-hour limit (100–500 emails/day theoretical), but personal Gmail spam filters flag outbound cold outreach that exceeds <strong>30–50 emails/day</strong>.
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "flex-start", gap: "8px" }}>
            <AlertCircle size={16} color="#ef4444" style={{ flexShrink: 0, marginTop: "2px" }} />
            <div>
              <strong>Domain Reputation:</strong> Aggressive sending above 30 emails/day from a personal address may lead to immediate Gmail throttling, spam folder placement, or temporary account suspension.
            </div>
          </div>
        </div>

        <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
          <button
            onClick={onCancel}
            style={{
              background: "#1e293b",
              border: "1px solid #475569",
              color: "#e2e8f0",
              padding: "10px 18px",
              borderRadius: "8px",
              fontWeight: 600,
              fontSize: "0.88rem",
              cursor: "pointer",
            }}
          >
            Keep Safe Cap (30)
          </button>
          <button
            onClick={onConfirm}
            style={{
              background: "#d97706",
              border: "none",
              color: "#ffffff",
              padding: "10px 18px",
              borderRadius: "8px",
              fontWeight: 700,
              fontSize: "0.88rem",
              cursor: "pointer",
              boxShadow: "0 2px 8px rgba(217, 119, 6, 0.4)",
            }}
          >
            I Understand, Set to {limit}
          </button>
        </div>
      </div>
    </div>
  );
}


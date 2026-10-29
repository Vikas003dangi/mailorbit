"use client";

import React, { useState } from "react";
import { ShieldAlert, RefreshCw, CheckCircle2, AlertTriangle, ArrowRight, Ban, Activity } from "lucide-react";

interface QuarantineSectionProps {
  notWorkingContacts: any[];
  replacements: any[];
  onReactivate: (contactId: string) => void;
  isDemoMode?: boolean;
}

export default function QuarantineSection({
  notWorkingContacts,
  replacements,
  onReactivate,
  isDemoMode = false,
}: QuarantineSectionProps) {
  const [activeSubTab, setActiveSubTab] = useState<"not_working" | "replacements">("not_working");

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, margin: "0 0 6px" }}>
            Quarantine & Replacement Registry
          </h1>
          <p style={{ color: "#94a3b8", fontSize: "0.92rem", margin: 0 }}>
            Automated dead email detection, MX verification quarantine, and on-the-fly lead replacement audit trail.
          </p>
        </div>

        {/* Tab Switcher */}
        <div style={{ display: "flex", background: "#111827", padding: "4px", borderRadius: "8px", border: "1px solid #1f2937" }}>
          <button
            onClick={() => setActiveSubTab("not_working")}
            style={{
              background: activeSubTab === "not_working" ? "#0284c7" : "transparent",
              color: activeSubTab === "not_working" ? "#ffffff" : "#94a3b8",
              border: "none",
              padding: "7px 14px",
              borderRadius: "6px",
              fontSize: "0.82rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Quarantined Leads ({notWorkingContacts.length})
          </button>
          <button
            onClick={() => setActiveSubTab("replacements")}
            style={{
              background: activeSubTab === "replacements" ? "#0284c7" : "transparent",
              color: activeSubTab === "replacements" ? "#ffffff" : "#94a3b8",
              border: "none",
              padding: "7px 14px",
              borderRadius: "6px",
              fontSize: "0.82rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Replacement Audit Log ({replacements.length})
          </button>
        </div>
      </div>

      {activeSubTab === "not_working" && (
        <div style={{ background: "#111827", borderRadius: "12px", border: "1px solid #1f2937", overflow: "hidden" }}>
          <div style={{ padding: "18px 20px", borderBottom: "1px solid #1f2937", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h3 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 600, color: "#f87171" }}>
                Identified "Not Working" Addresses
              </h3>
              <p style={{ margin: "4px 0 0", fontSize: "0.8rem", color: "#94a3b8" }}>
                These leads failed pre-send DNS MX validation, triggered a bounce, or opted out. Automatically excluded from dispatch.
              </p>
            </div>
            <span style={{ fontSize: "0.78rem", background: "rgba(239, 68, 68, 0.15)", color: "#ef4444", padding: "4px 10px", borderRadius: "999px", fontWeight: 700 }}>
              {notWorkingContacts.length} Dead Leads
            </span>
          </div>

          {notWorkingContacts.length === 0 ? (
            <div style={{ padding: "40px 20px", textAlign: "center", color: "#64748b" }}>
              <CheckCircle2 size={36} color="#22c55e" style={{ margin: "0 auto 12px" }} />
              <div style={{ fontWeight: 600, color: "#e2e8f0", marginBottom: "4px" }}>Clean Sender Domain Health</div>
              <div style={{ fontSize: "0.85rem" }}>No dead, bounced, or quarantined leads recorded in your account.</div>
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.86rem" }}>
                <thead>
                  <tr style={{ background: "rgba(15, 23, 42, 0.6)", borderBottom: "1px solid #1f2937", color: "#94a3b8" }}>
                    <th style={{ padding: "12px 18px", fontWeight: 600 }}>Recipient Email</th>
                    <th style={{ padding: "12px 18px", fontWeight: 600 }}>Contact / Company</th>
                    <th style={{ padding: "12px 18px", fontWeight: 600 }}>Quarantine Reason</th>
                    <th style={{ padding: "12px 18px", fontWeight: 600 }}>Status</th>
                    <th style={{ padding: "12px 18px", fontWeight: 600, textAlign: "right" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {notWorkingContacts.map((c) => (
                    <tr key={c.id} style={{ borderBottom: "1px solid #1f2937" }}>
                      <td style={{ padding: "14px 18px", fontWeight: 600, color: "#e2e8f0" }}>{c.email}</td>
                      <td style={{ padding: "14px 18px", color: "#94a3b8" }}>
                        {c.name || "—"} {c.company ? `(${c.company})` : ""}
                      </td>
                      <td style={{ padding: "14px 18px" }}>
                        <span
                          style={{
                            background: "rgba(239, 68, 68, 0.12)",
                            color: "#f87171",
                            padding: "3px 8px",
                            borderRadius: "4px",
                            fontSize: "0.78rem",
                            border: "1px solid rgba(239, 68, 68, 0.25)",
                          }}
                        >
                          {c.error || c.bounce_reason || "DNS MX Failure / Bounced"}
                        </span>
                      </td>
                      <td style={{ padding: "14px 18px" }}>
                        <span style={{ fontSize: "0.75rem", color: "#f87171", fontWeight: 700 }}>QUARANTINED</span>
                      </td>
                      <td style={{ padding: "14px 18px", textAlign: "right" }}>
                        <button
                          onClick={() => onReactivate(c.id)}
                          style={{
                            background: "rgba(56, 189, 248, 0.12)",
                            border: "1px solid #0284c7",
                            color: "#38bdf8",
                            padding: "5px 12px",
                            borderRadius: "6px",
                            fontSize: "0.78rem",
                            fontWeight: 600,
                            cursor: "pointer",
                          }}
                        >
                          Reactivate
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeSubTab === "replacements" && (
        <div style={{ background: "#111827", borderRadius: "12px", border: "1px solid #1f2937", overflow: "hidden" }}>
          <div style={{ padding: "18px 20px", borderBottom: "1px solid #1f2937", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h3 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 600, color: "#38bdf8" }}>
                On-The-Fly Replacement Audit Trail
              </h3>
              <p style={{ margin: "4px 0 0", fontSize: "0.8rem", color: "#94a3b8" }}>
                Whenever a lead fails pre-send verification, the dispatcher automatically pulls the next pending contact so your daily target is fulfilled.
              </p>
            </div>
            <span style={{ fontSize: "0.78rem", background: "rgba(56, 189, 248, 0.15)", color: "#38bdf8", padding: "4px 10px", borderRadius: "999px", fontWeight: 700 }}>
              {replacements.length} Replacements
            </span>
          </div>

          {replacements.length === 0 ? (
            <div style={{ padding: "40px 20px", textAlign: "center", color: "#64748b" }}>
              <Activity size={36} color="#38bdf8" style={{ margin: "0 auto 12px" }} />
              <div style={{ fontWeight: 600, color: "#e2e8f0", marginBottom: "4px" }}>No Replacements Triggered</div>
              <div style={{ fontSize: "0.85rem" }}>When a lead fails pre-send checks during live dispatch, replacement events will be logged here.</div>
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.86rem" }}>
                <thead>
                  <tr style={{ background: "rgba(15, 23, 42, 0.6)", borderBottom: "1px solid #1f2937", color: "#94a3b8" }}>
                    <th style={{ padding: "12px 18px", fontWeight: 600 }}>Original Lead (Dead)</th>
                    <th style={{ padding: "12px 18px", fontWeight: 600 }}>Action</th>
                    <th style={{ padding: "12px 18px", fontWeight: 600 }}>Replaced By (Fresh Lead)</th>
                    <th style={{ padding: "12px 18px", fontWeight: 600 }}>Reason</th>
                    <th style={{ padding: "12px 18px", fontWeight: 600 }}>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {replacements.map((r) => (
                    <tr key={r.id} style={{ borderBottom: "1px solid #1f2937" }}>
                      <td style={{ padding: "14px 18px", color: "#f87171", fontWeight: 600 }}>
                        {r.original_email}
                      </td>
                      <td style={{ padding: "14px 18px" }}>
                        <ArrowRight size={16} color="#38bdf8" />
                      </td>
                      <td style={{ padding: "14px 18px", color: "#34d399", fontWeight: 600 }}>
                        {r.replaced_by_email}
                      </td>
                      <td style={{ padding: "14px 18px", color: "#94a3b8", fontSize: "0.82rem" }}>
                        {r.reason}
                      </td>
                      <td style={{ padding: "14px 18px", color: "#64748b", fontSize: "0.8rem" }}>
                        {new Date(r.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


"use client";

import React, { useState } from "react";
import { Upload, FileText, CheckCircle2, AlertCircle } from "lucide-react";

interface DirectPasteModalProps {
  purposes: any[];
  selectedPurposeId: string;
  onSelectPurpose: (id: string) => void;
  onSubmit: (text: string, purposeId: string, batchSize: number, autoBatch: boolean) => Promise<void>;
  loading?: boolean;
}

export default function DirectPasteModal({
  purposes,
  selectedPurposeId,
  onSelectPurpose,
  onSubmit,
  loading = false,
}: DirectPasteModalProps) {
  const [pasteText, setPasteText] = useState("");
  const [batchSize, setBatchSize] = useState(25);
  const [autoBatch, setAutoBatch] = useState(true);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pasteText.trim()) return;
    await onSubmit(pasteText.trim(), selectedPurposeId, batchSize, autoBatch);
    setPasteText("");
  };

  return (
    <form onSubmit={handleSubmit} style={{ background: "#111827", padding: "20px", borderRadius: "10px", border: "1px solid #1f2937", marginBottom: "28px" }}>
      <h3 style={{ margin: "0 0 8px", fontSize: "1.05rem", color: "#38bdf8" }}>
        Direct Paste Contacts (Text Area)
      </h3>
      <p style={{ margin: "0 0 14px", fontSize: "0.82rem", color: "#9ca3af" }}>
        Paste leads directly. Supports commas, semicolons, or newlines (e.g. <code>alice@google.com, Bob Smith &lt;bob@stripe.com&gt;</code>).
      </p>

      <div style={{ marginBottom: "14px" }}>
        <textarea
          rows={5}
          value={pasteText}
          onChange={(e) => setPasteText(e.target.value)}
          placeholder={`recruiter@company.com\nJane Doe <jane@acme.org>; engineering-lead@startup.io`}
          style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", boxSizing: "border-box", fontFamily: "monospace", fontSize: "0.85rem" }}
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "14px", marginBottom: "16px" }}>
        <div>
          <label style={{ display: "block", fontSize: "0.78rem", color: "#9ca3af", marginBottom: "4px" }}>
            Target Campaign / Purpose
          </label>
          <select
            value={selectedPurposeId}
            onChange={(e) => onSelectPurpose(e.target.value)}
            style={{ width: "100%", padding: "8px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", fontSize: "0.82rem" }}
          >
            {purposes.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label style={{ display: "block", fontSize: "0.78rem", color: "#9ca3af", marginBottom: "4px" }}>
            Sub-Batch Size (Leads per batch)
          </label>
          <input
            type="number"
            min={5}
            max={50}
            value={batchSize}
            onChange={(e) => setBatchSize(parseInt(e.target.value) || 25)}
            style={{ width: "100%", padding: "8px", borderRadius: "6px", background: "#1f2937", border: "1px solid #374151", color: "#ffffff", fontSize: "0.82rem", boxSizing: "border-box" }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px", paddingTop: "20px" }}>
          <input
            type="checkbox"
            id="autoBatchCheck"
            checked={autoBatch}
            onChange={(e) => setAutoBatch(e.target.checked)}
            style={{ cursor: "pointer", width: "16px", height: "16px" }}
          />
          <label htmlFor="autoBatchCheck" style={{ fontSize: "0.82rem", color: "#cbd5e1", cursor: "pointer" }}>
            Auto-generate sub-batches
          </label>
        </div>
      </div>

      <button
        type="submit"
        disabled={!pasteText.trim() || loading}
        style={{
          background: loading || !pasteText.trim() ? "#0369a1" : "#0284c7",
          color: "#ffffff",
          border: "none",
          padding: "10px 20px",
          borderRadius: "6px",
          cursor: loading || !pasteText.trim() ? "not-allowed" : "pointer",
          fontWeight: 600,
          fontSize: "0.85rem",
        }}
      >
        {loading ? "Importing & Batching..." : "Process & Import Leads"}
      </button>
    </form>
  );
}


"use client";

import React from "react";
import { Droplets, RefreshCw, Layers, CheckCircle2, AlertCircle } from "lucide-react";

interface BatchItem {
  id: string;
  name?: string;
  batch_number?: number;
  status: string;
  total_contacts?: number;
  sent_count?: number;
  purpose_name?: string;
}

interface WaterFillVisualizerProps {
  batches: BatchItem[];
  dailyBudget?: number;
  allocations?: Array<{
    batch_id: string;
    batch_name: string;
    allocated_daily_count: number;
    pending_count: number;
  }>;
  onRunAutoBalance?: () => void;
  loading?: boolean;
}

export default function WaterFillVisualizer({
  batches,
  dailyBudget = 30,
  allocations = [],
  onRunAutoBalance,
  loading = false,
}: WaterFillVisualizerProps) {
  // Filter active and scheduled batches
  const activeBatches = batches.filter((b) =>
    ["ACTIVE", "SCHEDULED", "QUEUED"].includes(b.status)
  );

  // If backend allocations provided, use them; otherwise compute preview client-side
  let displayAllocations: Array<{ id: string; name: string; pending: number; allocated: number }> = [];

  if (allocations && allocations.length > 0) {
    displayAllocations = allocations.map((a) => ({
      id: a.batch_id,
      name: a.batch_name,
      pending: a.pending_count,
      allocated: a.allocated_daily_count,
    }));
  } else if (activeBatches.length > 0) {
    // Client-side water filling preview
    const k = activeBatches.length;
    const baseShare = Math.floor(dailyBudget / k);
    let remainder = dailyBudget % k;

    displayAllocations = activeBatches.map((b, idx) => {
      const pending = Math.max(0, (b.total_contacts || 25) - (b.sent_count || 0));
      const extra = idx < remainder ? 1 : 0;
      const allocated = Math.min(pending, baseShare + extra);
      return {
        id: b.id,
        name: b.name || `Batch #${b.batch_number || idx + 1}`,
        pending,
        allocated,
      };
    });
  }

  const totalAllocated = displayAllocations.reduce((sum, item) => sum + item.allocated, 0);

  return (
    <div
      style={{
        background: "#111827",
        border: "1px solid #1f2937",
        borderRadius: "12px",
        padding: "22px",
        marginBottom: "26px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "18px", flexWrap: "wrap", gap: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              background: "rgba(56, 189, 248, 0.12)",
              border: "1px solid #0284c7",
              borderRadius: "8px",
              padding: "8px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Droplets size={20} color="#38bdf8" />
          </div>
          <div>
            <h3 style={{ margin: "0 0 4px", fontSize: "1.1rem", fontWeight: 700, color: "#ffffff" }}>
              Single Sender Fair-Share Water-Filling
            </h3>
            <p style={{ margin: 0, fontSize: "0.82rem", color: "#94a3b8" }}>
              Dynamic daily allocation across active sub-batches • Safe cap: <strong>{dailyBudget} emails/day</strong>
            </p>
          </div>
        </div>

        {onRunAutoBalance && (
          <button
            onClick={onRunAutoBalance}
            disabled={loading}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: "#0284c7",
              border: "none",
              color: "#ffffff",
              padding: "8px 16px",
              borderRadius: "6px",
              fontWeight: 600,
              fontSize: "0.82rem",
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            {loading ? "Balancing..." : "Rebalance Allocations"}
          </button>
        )}
      </div>

      {/* Progress Bar of Daily Capacity */}
      <div style={{ marginBottom: "18px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem", marginBottom: "6px" }}>
          <span style={{ color: "#9ca3af" }}>Today's Total Scheduled Outreach</span>
          <span style={{ fontWeight: 700, color: totalAllocated <= dailyBudget ? "#38bdf8" : "#f59e0b" }}>
            {totalAllocated} / {dailyBudget} emails ({Math.round((totalAllocated / dailyBudget) * 100)}%)
          </span>
        </div>
        <div style={{ height: "8px", background: "#1f2937", borderRadius: "999px", overflow: "hidden", display: "flex" }}>
          {displayAllocations.map((alloc, idx) => {
            const widthPct = dailyBudget > 0 ? (alloc.allocated / dailyBudget) * 100 : 0;
            const colors = ["#38bdf8", "#818cf8", "#c084fc", "#34d399", "#f59e0b"];
            const color = colors[idx % colors.length];
            return (
              <div
                key={alloc.id}
                title={`${alloc.name}: ${alloc.allocated} emails`}
                style={{
                  width: `${widthPct}%`,
                  height: "100%",
                  background: color,
                  transition: "width 0.3s ease",
                }}
              />
            );
          })}
        </div>
      </div>

      {/* Batch Allocation List */}
      {displayAllocations.length === 0 ? (
        <div style={{ padding: "16px", textAlign: "center", color: "#64748b", fontSize: "0.85rem", border: "1px dashed #334155", borderRadius: "8px" }}>
          No active or scheduled sub-batches currently awaiting dispatch. Create a campaign and import leads to activate water-filling.
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "12px" }}>
          {displayAllocations.map((alloc, idx) => {
            const colors = ["#38bdf8", "#818cf8", "#c084fc", "#34d399", "#f59e0b"];
            const color = colors[idx % colors.length];
            return (
              <div
                key={alloc.id}
                style={{
                  background: "rgba(15, 23, 42, 0.6)",
                  border: "1px solid #1e293b",
                  borderLeft: `3px solid ${color}`,
                  borderRadius: "8px",
                  padding: "12px 14px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                  <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "#e2e8f0" }}>{alloc.name}</span>
                  <span style={{ fontSize: "0.75rem", background: "rgba(56, 189, 248, 0.15)", color: color, padding: "2px 8px", borderRadius: "999px", fontWeight: 700 }}>
                    {alloc.allocated} today
                  </span>
                </div>
                <div style={{ fontSize: "0.76rem", color: "#64748b" }}>
                  {alloc.pending} pending leads in sub-batch
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

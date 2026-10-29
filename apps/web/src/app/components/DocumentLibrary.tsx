"use client";

import React, { useRef } from "react";
import { FileText, Upload, Trash2, ExternalLink, Paperclip, ShieldCheck } from "lucide-react";

interface AttachmentItem {
  id: string;
  filename: string;
  file_url: string;
  size_bytes: number;
  content_type: string;
  created_at: string;
}

interface DocumentLibraryProps {
  attachments: AttachmentItem[];
  onUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDelete: (id: string) => void;
  uploading?: boolean;
}

export default function DocumentLibrary({
  attachments,
  onUpload,
  onDelete,
  uploading = false,
}: DocumentLibraryProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  return (
    <div style={{ background: "#111827", padding: "24px", borderRadius: "12px", border: "1px solid #1f2937", marginBottom: "26px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h3 style={{ margin: "0 0 4px", fontSize: "1.1rem", fontWeight: 700, color: "#ffffff", display: "flex", alignItems: "center", gap: "8px" }}>
            <FileText size={18} color="#38bdf8" />
            Resume & Document Library
          </h3>
          <p style={{ margin: 0, fontSize: "0.82rem", color: "#94a3b8" }}>
            Private authenticated document storage (Cloudinary). Supports PDF, DOCX, TXT up to 5 MB per document.
          </p>
        </div>

        <div>
          <input
            type="file"
            ref={fileInputRef}
            onChange={onUpload}
            accept=".pdf,.docx,.doc,.txt"
            style={{ display: "none" }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: "#0284c7",
              border: "none",
              color: "#ffffff",
              padding: "9px 16px",
              borderRadius: "8px",
              fontWeight: 600,
              fontSize: "0.85rem",
              cursor: uploading ? "not-allowed" : "pointer",
            }}
          >
            <Upload size={16} />
            {uploading ? "Uploading to Cloudinary..." : "Upload Document / Resume"}
          </button>
        </div>
      </div>

      {attachments.length === 0 ? (
        <div style={{ padding: "28px", textAlign: "center", color: "#64748b", border: "1px dashed #334155", borderRadius: "8px" }}>
          <FileText size={32} color="#475569" style={{ margin: "0 auto 8px" }} />
          <div style={{ fontWeight: 600, color: "#cbd5e1", marginBottom: "4px" }}>No Documents Uploaded</div>
          <div style={{ fontSize: "0.82rem" }}>Upload your resume (PDF/DOCX) to automatically link it to cold outreach emails.</div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {attachments.map((att) => (
            <div
              key={att.id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                background: "rgba(15, 23, 42, 0.6)",
                border: "1px solid #1e293b",
                borderRadius: "8px",
                padding: "12px 16px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div style={{ background: "rgba(56, 189, 248, 0.12)", padding: "8px", borderRadius: "6px" }}>
                  <Paperclip size={18} color="#38bdf8" />
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: "0.88rem", color: "#e2e8f0" }}>{att.filename}</div>
                  <div style={{ fontSize: "0.76rem", color: "#64748b" }}>
                    {formatBytes(att.size_bytes)} • Uploaded {new Date(att.created_at).toLocaleDateString()}
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                {att.file_url && att.file_url !== "#" && (
                  <a
                    href={att.file_url}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      color: "#38bdf8",
                      fontSize: "0.82rem",
                      textDecoration: "none",
                      padding: "6px 10px",
                      borderRadius: "6px",
                      background: "rgba(56, 189, 248, 0.08)",
                    }}
                  >
                    <ExternalLink size={14} /> View
                  </a>
                )}
                <button
                  onClick={() => onDelete(att.id)}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "#f87171",
                    padding: "6px",
                    borderRadius: "6px",
                    cursor: "pointer",
                  }}
                  title="Delete Document"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

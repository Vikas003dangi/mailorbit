import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "MailOrbit - AI Cold-Email Outreach Platform",
  description: "Schedule and dispatch automated personalized cold emails in smart batches with Fair-Share Water-Filling & BYOK AI.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <style>{`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          .spin {
            animation: spin 1s linear infinite;
          }
          * {
            box-sizing: border-box;
          }
          html, body {
            overflow-x: hidden;
            width: 100%;
          }
          /* Responsive utility styles */
          @media (max-width: 768px) {
            .app-sidebar {
              position: fixed !important;
              top: 57px !important;
              left: 0 !important;
              bottom: 0 !important;
              width: 270px !important;
              z-index: 1000 !important;
              box-shadow: 8px 0 24px rgba(0,0,0,0.8) !important;
              transform: translateX(-100%);
              transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
            }
            .app-sidebar.sidebar-open {
              transform: translateX(0) !important;
            }
            .sidebar-backdrop {
              position: fixed;
              top: 57px;
              left: 0;
              right: 0;
              bottom: 0;
              background: rgba(0, 0, 0, 0.65);
              backdrop-filter: blur(2px);
              z-index: 999;
            }
            .app-main-content {
              padding: 16px 12px !important;
            }
            .hide-on-mobile {
              display: none !important;
            }
            .show-on-mobile {
              display: flex !important;
            }
            .stats-grid-responsive {
              grid-template-columns: 1fr !important;
            }
            .responsive-2col {
              grid-template-columns: 1fr !important;
            }
            .responsive-flex-col {
              flex-direction: column !important;
            }
            .responsive-modal {
              width: 95vw !important;
              margin: 12px auto !important;
              padding: 18px !important;
              max-height: 90vh !important;
              overflow-y: auto !important;
            }
            .responsive-table-wrapper {
              overflow-x: auto !important;
              -webkit-overflow-scrolling: touch;
              width: 100%;
              max-width: 100%;
              display: block;
            }
          }
          @media (min-width: 769px) {
            .show-on-mobile {
              display: none !important;
            }
            .sidebar-backdrop {
              display: none !important;
            }
          }
        `}</style>
      </head>
      <body style={{ fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif", margin: 0, padding: 0, background: "#090d16", color: "#f8fafc" }}>
        {children}
      </body>
    </html>
  );
}



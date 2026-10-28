import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "MailOrbit - AI Cold-Email Outreach Platform",
  description: "Schedule and dispatch automated personalized cold emails in smart batches.",
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
        `}</style>
      </head>
      <body style={{ fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif", margin: 0, padding: 0, background: "#090d16", color: "#f8fafc" }}>
        {children}
      </body>
    </html>
  );
}


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
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0, padding: 0, background: "#0f172a", color: "#f8fafc" }}>
        {children}
      </body>
    </html>
  );
}


export default function HomePage() {
  return (
    <main style={{ maxWidth: "800px", margin: "80px auto", padding: "0 24px" }}>
      <header style={{ borderBottom: "1px solid #334155", paddingBottom: "24px", marginBottom: "32px" }}>
        <h1 style={{ fontSize: "2.5rem", fontWeight: 700, margin: 0, color: "#38bdf8" }}>
          MailOrbit
        </h1>
        <p style={{ color: "#94a3b8", fontSize: "1.1rem", marginTop: "8px" }}>
          AI Cold-Email Outreach Platform with smart batching, auto-topup, and zero-password relay.
        </p>
      </header>

      <section style={{ background: "#1e293b", borderRadius: "8px", padding: "24px", border: "1px solid #334155" }}>
        <h2 style={{ fontSize: "1.3rem", marginTop: 0, color: "#f1f5f9" }}>
          System Architecture Status (M0 Initialized)
        </h2>
        <ul style={{ lineHeight: "1.8", color: "#cbd5e1", paddingLeft: "20px" }}>
          <li><strong>Backend API:</strong> FastAPI on Render Free Tier</li>
          <li><strong>Database:</strong> Neon Serverless PostgreSQL 16 (auto-suspending)</li>
          <li><strong>Egress Relay:</strong> Google Apps Script per-user relay over HTTPS:443</li>
          <li><strong>Frontend:</strong> Next.js Static Export hosted on GitHub Pages</li>
          <li><strong>Worker:</strong> In-process queue runner behind unified JobQueue interface</li>
        </ul>
      </section>
    </main>
  );
}


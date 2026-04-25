import { useState } from "react";
import { Dashboard } from "./components/Dashboard";
import { ContractUpload } from "./components/ContractUpload";
import { GapAnalysis } from "./components/GapAnalysis";
import { RiskMap } from "./components/RiskMap";
import { RegisterView } from "./components/RegisterView";

const tabs = [
  { id: "dashboard", label: "Dashboard" },
  { id: "upload", label: "Upload" },
  { id: "gaps", label: "Gap Analysis" },
  { id: "risks", label: "Risk Map" },
  { id: "register", label: "Register" },
] as const;

type TabId = (typeof tabs)[number]["id"];

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>("dashboard");

  return (
    <div style={{ fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", background: "#f8fafc", minHeight: "100vh", color: "#1e293b" }}>
      <header style={{ background: "#0f172a", color: "#fff", padding: "0 2rem", display: "flex", alignItems: "center", justifyContent: "space-between", height: 56 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 32, height: 32, background: "#3b82f6", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 14 }}>RA</div>
          <span style={{ fontSize: 18, fontWeight: 700 }}>RegAgent</span>
          <span style={{ fontSize: 12, color: "#94a3b8", marginLeft: 4 }}>DORA Compliance Platform</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "#94a3b8" }}>
          <span style={{ width: 8, height: 8, background: "#22c55e", borderRadius: "50%", display: "inline-block" }} />
          Eurobank IS &middot; CRO View
        </div>
      </header>

      <nav style={{ background: "#fff", borderBottom: "1px solid #e2e8f0", padding: "0 2rem", display: "flex", gap: 0 }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "12px 20px",
              background: "none",
              border: "none",
              borderBottom: activeTab === tab.id ? "2px solid #3b82f6" : "2px solid transparent",
              color: activeTab === tab.id ? "#3b82f6" : "#64748b",
              fontWeight: activeTab === tab.id ? 600 : 400,
              fontSize: 14,
              cursor: "pointer",
              transition: "all 0.15s",
            }}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main style={{ padding: "24px 2rem", maxWidth: 1280, margin: "0 auto" }}>
        {activeTab === "dashboard" && <Dashboard />}
        {activeTab === "upload" && <ContractUpload />}
        {activeTab === "gaps" && <GapAnalysis />}
        {activeTab === "risks" && <RiskMap />}
        {activeTab === "register" && <RegisterView />}
      </main>
    </div>
  );
}

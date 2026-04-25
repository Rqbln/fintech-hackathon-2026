import { useState } from "react";
import { Dashboard } from "./components/Dashboard";
import { ContractUpload } from "./components/ContractUpload";
import { GapAnalysis } from "./components/GapAnalysis";
import { RiskMap } from "./components/RiskMap";
import { RegisterView } from "./components/RegisterView";
import { VendorGraph } from "./components/VendorGraph";
import type { AnalysisResult } from "./api";

const tabs = [
  { id: "dashboard",  label: "Dashboard" },
  { id: "upload",     label: "Upload" },
  { id: "graph",      label: "Vendor Graph" },
  { id: "gaps",       label: "Gap Analysis" },
  { id: "risks",      label: "Risk Map" },
  { id: "register",   label: "Register" },
] as const;

type TabId = (typeof tabs)[number]["id"];

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>("dashboard");
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);

  const handleAnalysisDone = (result: AnalysisResult) => {
    setAnalysisResult(result);
    setActiveTab("graph");
  };

  return (
    <div style={{ fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", background: "#f8fafc", minHeight: "100vh", color: "#1e293b" }}>
      <header style={{ background: "#0f172a", color: "#fff", padding: "0 2rem", display: "flex", alignItems: "center", justifyContent: "space-between", height: 56 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 32, height: 32, background: "#3b82f6", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 14 }}>RA</div>
          <span style={{ fontSize: 18, fontWeight: 700 }}>RegAgent</span>
          <span style={{ fontSize: 12, color: "#94a3b8", marginLeft: 4 }}>DORA Compliance Platform</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "#94a3b8" }}>
          {analysisResult && (
            <span style={{ fontSize: 11, padding: "3px 10px", background: "#1e3a5f", borderRadius: 20, color: "#93c5fd", marginRight: 8 }}>
              {analysisResult.vendor_name} — {analysisResult.evaluation.compliance_score}/100
            </span>
          )}
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
              position: "relative",
            }}
          >
            {tab.label}
            {/* Badge on Graph tab when result available */}
            {tab.id === "graph" && analysisResult && (
              <span style={{
                position: "absolute", top: 6, right: 4,
                width: 8, height: 8, borderRadius: "50%",
                background: analysisResult.evaluation.compliance_score >= 80 ? "#22c55e" : analysisResult.evaluation.compliance_score >= 50 ? "#f97316" : "#ef4444",
              }} />
            )}
          </button>
        ))}
      </nav>

      <main style={{ padding: "24px 2rem", maxWidth: 1280, margin: "0 auto" }}>
        {activeTab === "dashboard" && <Dashboard />}

        {activeTab === "upload" && (
          <ContractUpload onAnalysisDone={handleAnalysisDone} />
        )}

        {activeTab === "graph" && (
          analysisResult ? (
            <div>
              <div style={{ marginBottom: 20 }}>
                <h2 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 4px" }}>Vendor Graph</h2>
                <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
                  Relationship map — bank &rarr; ICT provider &rarr; sub-processors &middot; click a node to inspect alerts
                </p>
              </div>
              <VendorGraph
                nodes={analysisResult.graph.nodes}
                edges={analysisResult.graph.edges}
                meta={analysisResult.graph.meta}
              />
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "80px 24px", color: "#94a3b8" }}>
              <div style={{ fontSize: 40, marginBottom: 16 }}>&#128196;</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: "#475569", marginBottom: 8 }}>No analysis yet</div>
              <div style={{ fontSize: 13, marginBottom: 20 }}>Upload a vendor contract to generate the relationship graph</div>
              <button
                onClick={() => setActiveTab("upload")}
                style={{ padding: "10px 24px", background: "#3b82f6", color: "#fff", border: "none", borderRadius: 8, fontSize: 14, fontWeight: 600, cursor: "pointer" }}
              >
                Go to Upload
              </button>
            </div>
          )
        )}

        {activeTab === "gaps" && (
          <GapAnalysis
            alerts={analysisResult?.evaluation.alerts}
            categoryScores={analysisResult?.evaluation.category_scores}
            vendorName={analysisResult?.vendor_name}
            complianceScore={analysisResult?.evaluation.compliance_score}
          />
        )}

        {activeTab === "risks" && <RiskMap />}
        {activeTab === "register" && <RegisterView />}
      </main>
    </div>
  );
}

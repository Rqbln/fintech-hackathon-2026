import { Dashboard } from "./components/Dashboard";

export default function App() {
  return (
    <div>
      <header style={{ padding: "1rem 2rem", borderBottom: "1px solid #e5e7eb" }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700 }}>
          RegAgent <span style={{ fontWeight: 400, color: "#6b7280" }}>DORA Compliance</span>
        </h1>
      </header>
      <main style={{ padding: "2rem" }}>
        <Dashboard />
      </main>
    </div>
  );
}

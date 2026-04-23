import { useState, useEffect, useCallback } from "react";
import Dashboard from "./components/Dashboard";
import CitizenForm from "./components/CitizenForm";
import { getPrioritized, getStats } from "./services/api";
import { createWebSocket } from "./services/websocket";

// Register service worker for offline PWA support
if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js"));
}

// Simple client-side routing — /citizen shows citizen form, everything else shows dashboard
const isCitizenRoute = window.location.pathname === "/citizen";

export default function App() {
  if (isCitizenRoute) return <CitizenForm />;

  const [reports, setReports] = useState([]);
  const [stats, setStats] = useState({ total: 0, pending: 0, dispatched: 0, resolved: 0, critical: 0 });
  const [connected, setConnected] = useState(false);

  const loadData = useCallback(async () => {
    const [r, s] = await Promise.all([getPrioritized(), getStats()]);
    setReports(r);
    setStats(s);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const cleanup = createWebSocket((msg) => {
      setConnected(true);
      if (msg.type === "new_report") {
        setReports(prev => {
          const updated = [msg.report, ...prev];
          return updated.sort((a, b) => b.final_priority - a.final_priority);
        });
        setStats(s => ({ ...s, total: s.total + 1, pending: s.pending + 1,
          critical: msg.report.final_priority >= 8 ? s.critical + 1 : s.critical }));
      } else if (msg.type === "report_updated") {
        setReports(prev => prev.map(r => r.id === msg.report.id ? msg.report : r));
      }
    });
    return cleanup;
  }, []);

  return (
    <div className="h-screen flex flex-col bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800 shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-red-500 font-bold text-lg tracking-wide">AI DISASTER RESPONSE</span>
          <span className="text-xs text-gray-500 uppercase tracking-widest">Coordinator</span>
        </div>
        <div className="flex items-center gap-6 text-sm">
          <Stat label="Total" value={stats.total} />
          <Stat label="Pending" value={stats.pending} color="text-yellow-400" />
          <Stat label="Critical" value={stats.critical} color="text-red-400" />
          <Stat label="Dispatched" value={stats.dispatched} color="text-green-400" />
          <div className={`flex items-center gap-1.5 text-xs ${connected ? "text-green-400" : "text-gray-500"}`}>
            <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-400 animate-pulse" : "bg-gray-600"}`} />
            {connected ? "LIVE" : "Connecting..."}
          </div>
        </div>
      </header>

      <Dashboard reports={reports} onRefresh={loadData} />
    </div>
  );
}

function Stat({ label, value, color = "text-white" }) {
  return (
    <div className="text-center">
      <div className={`font-bold text-base ${color}`}>{value}</div>
      <div className="text-gray-500 text-xs">{label}</div>
    </div>
  );
}

import { useState } from "react";
import { dispatchReport } from "../services/api";

const priorityLabel = (p) => {
  if (p >= 8) return { text: "CRITICAL", cls: "text-red-400" };
  if (p >= 6) return { text: "HIGH", cls: "text-orange-400" };
  if (p >= 4) return { text: "MEDIUM", cls: "text-yellow-400" };
  return { text: "LOW", cls: "text-green-400" };
};

export default function ReportDetail({ report, onClose, onDispatched }) {
  const [responder, setResponder] = useState("");
  const [notes, setNotes] = useState("");
  const [dispatching, setDispatching] = useState(false);

  const pLabel = priorityLabel(report.final_priority);
  const reasoning = typeof report.ai_reasoning === "string"
    ? JSON.parse(report.ai_reasoning)
    : report.ai_reasoning || {};

  async function handleDispatch() {
    if (!responder.trim()) return;
    setDispatching(true);
    await dispatchReport(report.id, responder, notes);
    setDispatching(false);
    onDispatched();
    onClose();
  }

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <div>
            <span className="text-xs text-gray-400 uppercase tracking-widest">Report #{report.id}</span>
            <div className="flex items-center gap-3 mt-0.5">
              <span className={`text-2xl font-bold ${pLabel.cls}`}>{report.final_priority.toFixed(1)}</span>
              <span className={`text-sm font-semibold ${pLabel.cls}`}>{pLabel.text}</span>
              <span className="text-xs text-gray-500 capitalize">{report.status}</span>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">✕</button>
        </div>

        <div className="p-4 space-y-4">
          {/* Report text */}
          <div>
            <label className="text-xs text-gray-400 uppercase tracking-widest">Report</label>
            <p className="mt-1 text-gray-100 text-sm leading-relaxed">{report.text_message}</p>
          </div>

          {/* Image */}
          {report.image_path && (
            <div>
              <label className="text-xs text-gray-400 uppercase tracking-widest">Image</label>
              <img
                src={`/uploads/${report.image_path.split("/").pop()}`}
                alt="Report"
                className="mt-1 rounded-lg w-full object-cover max-h-40"
              />
            </div>
          )}

          {/* AI Reasoning */}
          <div className="bg-gray-800 rounded-lg p-3 space-y-2 font-mono text-xs">
            <div className="text-green-400 font-semibold mb-2">AI REASONING</div>
            <Row k="nlp_class" v={`${reasoning.nlp_class} (conf: ${(reasoning.nlp_confidence * 100).toFixed(0)}%)`} />
            <Row k="image_damage" v={reasoning.image_damage} />
            <Row k="image_severity" v={reasoning.image_severity} />
            <Row k="location_cluster" v={reasoning.location_cluster} />
            <div className="border-t border-gray-700 pt-2 mt-2">
              <div className="text-gray-400">Score Breakdown:</div>
              <Row k="  text_score" v={`${reasoning.text_score?.toFixed(1)} × 0.6`} />
              <Row k="  image_score" v={`${reasoning.image_score?.toFixed(1)} × 0.3`} />
              <Row k="  location_risk" v={`${reasoning.location_risk?.toFixed(1)} × 0.1`} />
              <Row k="  FINAL" v={report.final_priority.toFixed(2)} highlight />
            </div>
          </div>

          {/* GPS */}
          {report.latitude && (
            <div className="text-xs text-gray-400">
              GPS: {report.latitude.toFixed(5)}, {report.longitude.toFixed(5)}
            </div>
          )}

          {/* Dispatch */}
          {report.status === "pending" && (
            <div className="border-t border-gray-800 pt-3 space-y-2">
              <label className="text-xs text-gray-400 uppercase tracking-widest">Dispatch</label>
              <input
                value={responder}
                onChange={(e) => setResponder(e.target.value)}
                placeholder="Responder ID / Team"
                className="w-full bg-gray-800 rounded px-3 py-2 text-sm text-white placeholder-gray-500 border border-gray-700 focus:border-red-500 outline-none"
              />
              <input
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Notes (optional)"
                className="w-full bg-gray-800 rounded px-3 py-2 text-sm text-white placeholder-gray-500 border border-gray-700 focus:border-red-500 outline-none"
              />
              <button
                onClick={handleDispatch}
                disabled={!responder.trim() || dispatching}
                className="w-full py-2 bg-red-600 hover:bg-red-500 disabled:opacity-40 rounded text-sm font-semibold transition-colors"
              >
                {dispatching ? "Dispatching..." : "Dispatch Responder"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ k, v, highlight }) {
  return (
    <div className="flex gap-2">
      <span className="text-gray-500 shrink-0">{k}:</span>
      <span className={highlight ? "text-yellow-400 font-bold" : "text-gray-300"}>{v}</span>
    </div>
  );
}

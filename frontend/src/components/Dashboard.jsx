import { useState } from "react";
import ReportMap from "./ReportMap";
import PriorityList from "./PriorityList";
import ReportDetail from "./ReportDetail";
import ReportForm from "./ReportForm";

export default function Dashboard({ reports, onRefresh }) {
  const [selectedReport, setSelectedReport] = useState(null);
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Left: Map */}
      <div className="flex-1 relative">
        <ReportMap reports={reports} onSelectReport={setSelectedReport} />
      </div>

      {/* Right: List */}
      <div className="w-96 flex flex-col bg-gray-900 border-l border-gray-800">
        <div className="p-3 border-b border-gray-800">
          <button
            onClick={() => setShowForm(true)}
            className="w-full py-2 bg-red-600 hover:bg-red-500 rounded text-sm font-semibold transition-colors"
          >
            + Submit Report
          </button>
        </div>
        <PriorityList reports={reports} onSelect={setSelectedReport} selected={selectedReport} />
      </div>

      {/* Modals */}
      {selectedReport && (
        <ReportDetail
          report={selectedReport}
          onClose={() => setSelectedReport(null)}
          onDispatched={onRefresh}
        />
      )}
      {showForm && (
        <ReportForm
          onClose={() => setShowForm(false)}
          onSubmitted={() => { setShowForm(false); onRefresh(); }}
        />
      )}
    </div>
  );
}

const priorityColor = (p) => {
  if (p >= 8) return { bg: "bg-red-900/40", border: "border-red-600", badge: "bg-red-600", label: "CRITICAL" };
  if (p >= 6) return { bg: "bg-orange-900/30", border: "border-orange-500", badge: "bg-orange-500", label: "HIGH" };
  if (p >= 4) return { bg: "bg-yellow-900/20", border: "border-yellow-500", badge: "bg-yellow-500", label: "MED" };
  return { bg: "bg-gray-800/50", border: "border-gray-600", badge: "bg-gray-500", label: "LOW" };
};

const statusColor = (s) => {
  if (s === "dispatched") return "text-green-400";
  if (s === "resolved") return "text-gray-400";
  return "text-yellow-400";
};

export default function PriorityList({ reports, onSelect, selected }) {
  return (
    <div className="flex-1 overflow-y-auto">
      {reports.length === 0 && (
        <div className="p-8 text-center text-gray-500 text-sm">
          No reports yet. Submit one or run the simulator.
        </div>
      )}
      {reports.map((r) => {
        const c = priorityColor(r.final_priority);
        const isSelected = selected?.id === r.id;
        return (
          <div
            key={r.id}
            onClick={() => onSelect(r)}
            className={`px-4 py-3 border-l-2 cursor-pointer transition-all ${c.bg} ${c.border}
              ${isSelected ? "ring-1 ring-white/20" : "hover:brightness-110"}
              border-b border-gray-800`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-100 leading-snug truncate">{r.text_message}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-gray-400">{r.nlp_category || "—"}</span>
                  {r.image_class && r.image_class !== "normal" && (
                    <span className="text-xs text-blue-400">· {r.image_class.replace("_", " ")}</span>
                  )}
                </div>
              </div>
              <div className="text-right shrink-0">
                <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-bold text-white ${c.badge}`}>
                  {r.final_priority.toFixed(1)}
                </span>
                <div className={`text-xs mt-0.5 ${statusColor(r.status)}`}>{r.status}</div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

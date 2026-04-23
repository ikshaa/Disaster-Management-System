import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const markerColor = (priority) => {
  if (priority >= 8) return "#ef4444";
  if (priority >= 6) return "#f97316";
  if (priority >= 4) return "#eab308";
  return "#22c55e";
};

function HeatLayer({ reports }) {
  const map = useMap();
  const heatRef = useRef(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const L = window.L;
    if (!L || !L.heatLayer) return;

    if (heatRef.current) {
      map.removeLayer(heatRef.current);
    }

    const points = reports
      .filter((r) => r.latitude && r.longitude)
      .map((r) => [r.latitude, r.longitude, r.final_priority / 10]);

    if (points.length > 0) {
      heatRef.current = L.heatLayer(points, {
        radius: 40,
        blur: 25,
        maxZoom: 17,
        gradient: { 0.2: "blue", 0.5: "orange", 1.0: "red" },
      }).addTo(map);
    }

    return () => {
      if (heatRef.current) map.removeLayer(heatRef.current);
    };
  }, [reports, map]);

  return null;
}

export default function ReportMap({ reports, onSelectReport }) {
  const geoReports = reports.filter((r) => r.latitude && r.longitude);
  const center = geoReports.length > 0
    ? [geoReports[0].latitude, geoReports[0].longitude]
    : [43.0831, -76.1474]; // Default: Rochester, NY (RIT area)

  return (
    <MapContainer
      center={center}
      zoom={13}
      style={{ height: "100%", width: "100%" }}
      className="z-0"
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; OpenStreetMap contributors'
      />

      {geoReports.map((r) => (
        <CircleMarker
          key={r.id}
          center={[r.latitude, r.longitude]}
          radius={8 + r.final_priority * 0.8}
          pathOptions={{
            color: markerColor(r.final_priority),
            fillColor: markerColor(r.final_priority),
            fillOpacity: 0.8,
            weight: 2,
          }}
          eventHandlers={{ click: () => onSelectReport(r) }}
        >
          <Popup>
            <div className="text-sm">
              <strong>Priority: {r.final_priority.toFixed(1)}</strong>
              <p>{r.text_message.substring(0, 80)}...</p>
              <p className="text-gray-500 text-xs">{r.nlp_category}</p>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}

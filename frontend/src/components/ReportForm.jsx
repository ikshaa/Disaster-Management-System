import { useState } from "react";
import { submitReport } from "../services/api";

export default function ReportForm({ onClose, onSubmitted }) {
  const [text, setText] = useState("");
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    if (!text.trim()) return;
    setLoading(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("text_message", text);
      if (lat) fd.append("latitude", lat);
      if (lng) fd.append("longitude", lng);
      if (image) fd.append("image", image);
      await submitReport(fd);
      onSubmitted();
    } catch (err) {
      setError("Failed to submit. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  function useMyLocation() {
    navigator.geolocation?.getCurrentPosition((pos) => {
      setLat(pos.coords.latitude.toFixed(6));
      setLng(pos.coords.longitude.toFixed(6));
    });
  }

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <h2 className="font-semibold text-white">Submit Disaster Report</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-3">
          <div>
            <label className="text-xs text-gray-400 uppercase tracking-widest block mb-1">
              Describe the situation *
            </label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={3}
              placeholder="e.g. Building collapsed, 3 people trapped inside..."
              className="w-full bg-gray-800 rounded px-3 py-2 text-sm text-white placeholder-gray-500 border border-gray-700 focus:border-red-500 outline-none resize-none"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Latitude</label>
              <input
                value={lat}
                onChange={(e) => setLat(e.target.value)}
                placeholder="43.0831"
                className="w-full bg-gray-800 rounded px-3 py-2 text-sm text-white placeholder-gray-500 border border-gray-700 focus:border-red-500 outline-none"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Longitude</label>
              <input
                value={lng}
                onChange={(e) => setLng(e.target.value)}
                placeholder="-76.1474"
                className="w-full bg-gray-800 rounded px-3 py-2 text-sm text-white placeholder-gray-500 border border-gray-700 focus:border-red-500 outline-none"
              />
            </div>
          </div>

          <button
            type="button"
            onClick={useMyLocation}
            className="text-xs text-blue-400 hover:text-blue-300 underline"
          >
            Use my location
          </button>

          <div>
            <label className="text-xs text-gray-400 uppercase tracking-widest block mb-1">
              Photo (optional)
            </label>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setImage(e.target.files[0])}
              className="w-full text-sm text-gray-300 file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:bg-gray-700 file:text-white file:text-xs hover:file:bg-gray-600"
            />
          </div>

          {error && <p className="text-red-400 text-xs">{error}</p>}

          <button
            type="submit"
            disabled={loading || !text.trim()}
            className="w-full py-2.5 bg-red-600 hover:bg-red-500 disabled:opacity-40 rounded font-semibold text-sm transition-colors"
          >
            {loading ? "Analyzing & Submitting..." : "Submit Report"}
          </button>
        </form>
      </div>
    </div>
  );
}

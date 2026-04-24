import { useState, useEffect } from "react";
import { submitReport } from "../services/api";

export default function ReportForm({ onClose, onSubmitted }) {
  const [text, setText] = useState("");
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [locLoading, setLocLoading] = useState(false);
  const [locError, setLocError] = useState("");
  const [error, setError] = useState("");

  // Auto-detect location when form opens
  useEffect(() => {
    getLocation();
  }, []);

  function getLocation() {
    if (!navigator.geolocation) {
      setLocError("Geolocation not supported. Enter coordinates manually.");
      return;
    }
    setLocLoading(true);
    setLocError("");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude.toFixed(6));
        setLng(pos.coords.longitude.toFixed(6));
        setLocLoading(false);
      },
      () => {
        setLocLoading(false);
        setLocError("Could not get location. Please enter coordinates manually.");
      },
      { timeout: 8000 }
    );
  }

  const locationReady = lat.trim() !== "" && lng.trim() !== "";
  const canSubmit = !loading && text.trim() && locationReady;

  async function handleSubmit(e) {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("text_message", text);
      fd.append("latitude", lat);
      fd.append("longitude", lng);
      if (image) fd.append("image", image);
      await submitReport(fd);
      onSubmitted();
    } catch (err) {
      setError("Failed to submit. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <h2 className="font-semibold text-white">Submit Disaster Report</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-3">
          {/* Description */}
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

          {/* Location */}
          <div>
            <label className="text-xs text-gray-400 uppercase tracking-widest block mb-1">
              Location * <span className="text-red-400">(required)</span>
            </label>

            {/* Auto-detect status */}
            {locLoading && (
              <div className="flex items-center gap-2 text-xs text-blue-400 mb-2">
                <span className="animate-spin">⟳</span> Detecting your location...
              </div>
            )}
            {!locLoading && locationReady && (
              <div className="flex items-center gap-2 text-xs text-green-400 mb-2">
                ✓ Location detected
              </div>
            )}
            {locError && (
              <div className="text-xs text-orange-400 mb-2">{locError}</div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <div>
                <input
                  value={lat}
                  onChange={(e) => setLat(e.target.value)}
                  placeholder="Latitude *"
                  required
                  className={`w-full bg-gray-800 rounded px-3 py-2 text-sm text-white placeholder-gray-500 border outline-none
                    ${lat ? "border-green-600" : "border-red-600"} focus:border-red-500`}
                />
              </div>
              <div>
                <input
                  value={lng}
                  onChange={(e) => setLng(e.target.value)}
                  placeholder="Longitude *"
                  required
                  className={`w-full bg-gray-800 rounded px-3 py-2 text-sm text-white placeholder-gray-500 border outline-none
                    ${lng ? "border-green-600" : "border-red-600"} focus:border-red-500`}
                />
              </div>
            </div>
            <button type="button" onClick={getLocation} className="text-xs text-blue-400 hover:text-blue-300 underline mt-1">
              📍 Re-detect my location
            </button>
          </div>

          {/* Image */}
          <div>
            <label className="text-xs text-gray-400 uppercase tracking-widest block mb-1">Photo (optional)</label>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setImage(e.target.files[0])}
              className="w-full text-sm text-gray-300 file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:bg-gray-700 file:text-white file:text-xs hover:file:bg-gray-600"
            />
          </div>

          {error && <p className="text-red-400 text-xs">{error}</p>}
          {!locationReady && !locLoading && (
            <p className="text-red-400 text-xs">📍 Location is required before submitting.</p>
          )}

          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full py-2.5 bg-red-600 hover:bg-red-500 disabled:opacity-40 disabled:cursor-not-allowed rounded font-semibold text-sm transition-colors"
          >
            {loading ? "Analyzing & Submitting..." : !locationReady ? "Waiting for location..." : "Submit Report"}
          </button>
        </form>
      </div>
    </div>
  );
}

import { useState, useEffect, useCallback } from "react";

const QUEUE_KEY = "disaster_offline_queue";
const RELAY_KEY = "disaster_relay_url";

function useNetwork() {
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => { window.removeEventListener("online", on); window.removeEventListener("offline", off); };
  }, []);
  return online;
}

function loadQueue() {
  try { return JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]"); }
  catch { return []; }
}
function saveQueue(q) { localStorage.setItem(QUEUE_KEY, JSON.stringify(q)); }

export default function CitizenForm() {
  const online = useNetwork();
  const [text, setText] = useState("");
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [image, setImage] = useState(null);
  const [relayUrl, setRelayUrl] = useState(() => localStorage.getItem(RELAY_KEY) || "");
  const [showSettings, setShowSettings] = useState(false);
  const [status, setStatus] = useState(null); // {type: 'success'|'error', msg}
  const [loading, setLoading] = useState(false);
  const [queueCount, setQueueCount] = useState(loadQueue().length);
  const [syncing, setSyncing] = useState(false);

  const targetUrl = relayUrl.trim() || null;
  const submitEndpoint = targetUrl ? `${targetUrl}/submit` : "/api/v1/reports";

  // Auto-sync when coming back online
  const syncQueue = useCallback(async () => {
    const queue = loadQueue();
    if (queue.length === 0) return;
    setSyncing(true);
    const remaining = [];
    for (const item of queue) {
      try {
        const fd = new FormData();
        fd.append("text_message", item.text_message);
        if (item.latitude) fd.append("latitude", item.latitude);
        if (item.longitude) fd.append("longitude", item.longitude);
        await fetch(submitEndpoint, { method: "POST", body: fd });
      } catch {
        remaining.push(item);
      }
    }
    saveQueue(remaining);
    setQueueCount(remaining.length);
    setSyncing(false);
    if (remaining.length === 0 && queue.length > 0) {
      setStatus({ type: "success", msg: `✓ ${queue.length} offline report(s) synced successfully.` });
    }
  }, [submitEndpoint]);

  useEffect(() => {
    if (online) syncQueue();
  }, [online, syncQueue]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!text.trim()) return;
    setLoading(true);
    setStatus(null);

    const fd = new FormData();
    fd.append("text_message", text);
    if (lat) fd.append("latitude", lat);
    if (lng) fd.append("longitude", lng);
    if (image) fd.append("image", image);

    if (!online) {
      // Save to offline queue (no image — can't reliably serialize File offline)
      const q = loadQueue();
      q.push({ text_message: text, latitude: lat, longitude: lng, queued_at: new Date().toISOString() });
      saveQueue(q);
      setQueueCount(q.length);
      setStatus({ type: "offline", msg: `📴 Offline — report saved locally. Will auto-sync when reconnected. (${q.length} queued)` });
      setText(""); setLat(""); setLng(""); setImage(null);
      setLoading(false);
      return;
    }

    try {
      const r = await fetch(submitEndpoint, { method: "POST", body: fd });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      const score = d.final_priority ?? "—";
      setStatus({ type: "success", msg: `✓ Report submitted! AI priority score: ${score}/10` });
      setText(""); setLat(""); setLng(""); setImage(null);
    } catch (err) {
      setStatus({ type: "error", msg: `Failed to submit. Saving offline. (${err.message})` });
      const q = loadQueue();
      q.push({ text_message: text, latitude: lat, longitude: lng, queued_at: new Date().toISOString() });
      saveQueue(q);
      setQueueCount(q.length);
    } finally {
      setLoading(false);
    }
  }

  function useMyLocation() {
    navigator.geolocation?.getCurrentPosition((p) => {
      setLat(p.coords.latitude.toFixed(6));
      setLng(p.coords.longitude.toFixed(6));
    });
  }

  function saveRelayUrl(url) {
    setRelayUrl(url);
    localStorage.setItem(RELAY_KEY, url);
  }

  const statusColors = {
    success: "bg-green-900/50 border-green-600 text-green-300",
    error: "bg-red-900/50 border-red-600 text-red-300",
    offline: "bg-orange-900/50 border-orange-600 text-orange-300",
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="bg-red-700 rounded-t-xl p-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-white font-bold text-lg">🆘 Submit Disaster Report</h1>
              <p className="text-red-200 text-xs mt-0.5">AI Disaster Response Coordinator</p>
            </div>
            <button onClick={() => setShowSettings(!showSettings)} className="text-red-200 hover:text-white text-xs underline">
              ⚙ Relay
            </button>
          </div>

          {/* Network status */}
          <div className={`mt-2 flex items-center gap-2 text-xs font-medium px-2 py-1 rounded-full w-fit
            ${online ? "bg-green-900/60 text-green-300" : "bg-orange-900/60 text-orange-300"}`}>
            <span className={`w-2 h-2 rounded-full ${online ? "bg-green-400 animate-pulse" : "bg-orange-400"}`} />
            {online
              ? (targetUrl ? `📡 Connected via relay: ${targetUrl}` : "🌐 Online — direct to hub")
              : "📴 Offline — reports saved locally"}
          </div>
        </div>

        {/* Settings panel */}
        {showSettings && (
          <div className="bg-gray-800 border-x border-gray-700 p-3">
            <label className="text-xs text-gray-400 uppercase tracking-widest block mb-1">Relay Node URL (leave blank for direct)</label>
            <input
              value={relayUrl}
              onChange={(e) => saveRelayUrl(e.target.value)}
              placeholder="http://192.168.1.100:8001"
              className="w-full bg-gray-900 rounded px-3 py-2 text-sm text-white border border-gray-600 focus:border-red-500 outline-none"
            />
            <p className="text-xs text-gray-500 mt-1">Connect to a mesh relay node on your local WiFi instead of the internet hub.</p>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-700 border-t-0 rounded-b-xl p-4 space-y-3">
          {status && (
            <div className={`text-sm p-3 rounded border ${statusColors[status.type]}`}>
              {status.msg}
            </div>
          )}

          {queueCount > 0 && online && !syncing && (
            <div className="text-xs bg-blue-900/40 border border-blue-700 text-blue-300 rounded px-3 py-2 flex items-center justify-between">
              <span>{queueCount} report(s) queued offline</span>
              <button type="button" onClick={syncQueue} className="underline ml-2">Sync now</button>
            </div>
          )}
          {syncing && (
            <div className="text-xs bg-blue-900/40 border border-blue-700 text-blue-300 rounded px-3 py-2">
              Syncing offline reports...
            </div>
          )}

          <div>
            <label className="text-xs text-gray-400 uppercase tracking-widest block mb-1">Describe the situation *</label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={3}
              required
              placeholder="e.g. Building collapsed, 3 people trapped inside..."
              className="w-full bg-gray-800 rounded px-3 py-2 text-sm text-white placeholder-gray-500 border border-gray-700 focus:border-red-500 outline-none resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Latitude</label>
              <input value={lat} onChange={(e) => setLat(e.target.value)} placeholder="43.0831"
                className="w-full bg-gray-800 rounded px-3 py-2 text-sm text-white placeholder-gray-500 border border-gray-700 focus:border-red-500 outline-none" />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Longitude</label>
              <input value={lng} onChange={(e) => setLng(e.target.value)} placeholder="-76.1474"
                className="w-full bg-gray-800 rounded px-3 py-2 text-sm text-white placeholder-gray-500 border border-gray-700 focus:border-red-500 outline-none" />
            </div>
          </div>
          <button type="button" onClick={useMyLocation} className="text-xs text-blue-400 hover:text-blue-300 underline">
            📍 Use my location
          </button>

          <div>
            <label className="text-xs text-gray-400 uppercase tracking-widest block mb-1">Photo (optional)</label>
            <input type="file" accept="image/*" capture="environment"
              onChange={(e) => setImage(e.target.files[0])}
              className="w-full text-sm text-gray-300 file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:bg-gray-700 file:text-white file:text-xs hover:file:bg-gray-600" />
            {!online && <p className="text-xs text-gray-500 mt-1">Images cannot be saved offline — text + GPS will be queued.</p>}
          </div>

          <button type="submit" disabled={loading || !text.trim()}
            className="w-full py-2.5 bg-red-600 hover:bg-red-500 disabled:opacity-40 rounded font-semibold text-sm transition-colors">
            {loading ? "Submitting..." : online ? "Submit Report" : "Save Offline"}
          </button>

          <p className="text-xs text-gray-600 text-center">
            {online ? "Report goes directly to AI triage system" : "Saved locally — auto-syncs when back online"}
          </p>
        </form>
      </div>
    </div>
  );
}

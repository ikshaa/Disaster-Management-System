// Auto-detect WebSocket URL: respects VITE_API_URL in production,
// falls back to localhost backend in dev, swaps http→ws automatically
function getWsUrl() {
  const apiUrl = import.meta.env.VITE_API_URL;
  if (apiUrl) {
    return apiUrl.replace(/^https?/, m => m === "https" ? "wss" : "ws") + "/ws/live";
  }
  // Dev fallback
  return "ws://localhost:8000/ws/live";
}
const WS_URL = getWsUrl();

export function createWebSocket(onMessage, onConnect, onDisconnect) {
  let ws;
  let reconnectTimer;

  function connect() {
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      onConnect?.();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (e) {
        console.error("WS parse error", e);
      }
    };

    ws.onclose = () => {
      onDisconnect?.();
      reconnectTimer = setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();
  }

  connect();

  return () => {
    clearTimeout(reconnectTimer);
    ws?.close();
  };
}

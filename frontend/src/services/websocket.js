const WS_URL = "ws://localhost:8000/ws/live";

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

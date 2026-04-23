const WS_URL = "ws://localhost:8000/ws/live";

export function createWebSocket(onMessage) {
  let ws;
  let reconnectTimer;

  function connect() {
    ws = new WebSocket(WS_URL);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (e) {
        console.error("WS parse error", e);
      }
    };

    ws.onclose = () => {
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

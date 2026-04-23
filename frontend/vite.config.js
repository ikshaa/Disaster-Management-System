import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": "http://localhost:8000",
      "/uploads": "http://localhost:8000",
      // Phase 2: relay endpoints proxied for dev
      "/submit": "http://localhost:8001",
      "/sync": "http://localhost:8001",
      "/status": "http://localhost:8001",
    },
  },
});

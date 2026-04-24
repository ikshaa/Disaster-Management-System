import axios from "axios";

// Production: VITE_API_URL points to deployed backend (e.g. https://rescue-ai-api.onrender.com)
// Development: empty string → uses Vite proxy in vite.config.js
const API_HOST = import.meta.env.VITE_API_URL || "";
const BASE = `${API_HOST}/api/v1`;

export const getPrioritized = () => axios.get(`${BASE}/prioritized`).then(r => r.data);
export const getReport = (id) => axios.get(`${BASE}/reports/${id}`).then(r => r.data);
export const getStats = () => axios.get(`${BASE}/stats`).then(r => r.data);
export const getHotspots = () => axios.get(`${BASE}/hotspots`).then(r => r.data);

export const submitReport = (formData) =>
  axios.post(`${BASE}/reports`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  }).then(r => r.data);

export const dispatchReport = (id, responder_id, notes = "") =>
  axios.post(`${BASE}/reports/${id}/dispatch`, { responder_id, notes }).then(r => r.data);

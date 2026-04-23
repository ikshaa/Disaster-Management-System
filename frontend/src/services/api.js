import axios from "axios";

const BASE = "/api/v1";

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

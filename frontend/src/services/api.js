// src/services/api.js
import axios from "axios";

// ✅ Use environment variable if provided, otherwise relative paths
// In production on Azure, API calls will be like `/api/...` (same domain as frontend).
// In local dev, you can set REACT_APP_API_BASE=http://127.0.0.1:8000 in frontend/.env
const API_BASE = (process.env.REACT_APP_API_BASE || "").replace(/\/$/, "");

const api = axios.create({
  baseURL: API_BASE || "", // empty means relative URLs (good for production)
  timeout: 60000, // 60s timeout
});

// -------------------------
// Request Interceptor
// -------------------------
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // Ensure JSON headers unless explicitly overridden
    if (!config.headers["Content-Type"]) {
      config.headers["Content-Type"] = "application/json";
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// -------------------------
// Response Interceptor
// -------------------------
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Normalize error message
    const message =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      error.message ||
      "Network error";

    // Useful for UI display
    const friendlyError = {
      ...error,
      friendlyMessage: message,
      status: error?.response?.status,
    };

    return Promise.reject(friendlyError);
  }
);

export default api;

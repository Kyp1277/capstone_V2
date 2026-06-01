import axios from "axios";
import { API_BASE_URL, state } from "./state.js";

export const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000
});

http.interceptors.request.use((config) => {
  if (state.auth.token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${state.auth.token}`;
  }
  return config;
});

export function apiErrorMessage(error, fallback = "Layanan sedang bermasalah. Coba beberapa saat lagi.") {
  const detail = error?.response?.data?.detail || error?.response?.data?.error;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        const location = Array.isArray(item.loc) ? item.loc.filter((part) => part !== "body").join(".") : "";
        const message = item.msg || "Validasi request gagal.";
        return location ? `${location}: ${message}` : message;
      })
      .join(" ");
  }

  return error?.message || fallback;
}

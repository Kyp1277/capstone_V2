import { API_BASE_URL, state } from "./state.js";

const DEFAULT_TIMEOUT_MS = 150000;

export const http = {
  get(url, config = {}) {
    return request({ ...config, method: "GET", url });
  },

  post(url, data, config = {}) {
    return request({ ...config, method: "POST", url, data });
  },

  patch(url, data, config = {}) {
    return request({ ...config, method: "PATCH", url, data });
  },

  request
};

async function request({ url, method = "GET", data, params, headers = {}, timeout = DEFAULT_TIMEOUT_MS, ...options }) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeout);
  const requestUrl = buildUrl(url, params);
  const requestHeaders = { ...headers };
  const init = {
    ...options,
    method,
    headers: requestHeaders,
    signal: controller.signal
  };

  if (state.auth.token) {
    requestHeaders.Authorization = `Bearer ${state.auth.token}`;
  }

  if (data instanceof FormData) {
    init.body = data;
  } else if (data !== undefined) {
    requestHeaders["Content-Type"] = requestHeaders["Content-Type"] || "application/json";
    init.body = JSON.stringify(data);
  }

  try {
    const response = await fetch(requestUrl, init);
    const payload = await parseResponse(response);

    if (!response.ok) {
      throw createHttpError(response, payload);
    }

    return {
      data: payload,
      status: response.status,
      headers: response.headers
    };
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Request timeout. Coba beberapa saat lagi.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function buildUrl(path, params) {
  const url = new URL(path, API_BASE_URL);

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, value);
    }
  });

  return url.toString();
}

async function parseResponse(response) {
  const text = await response.text();
  if (!text) {
    return {};
  }

  try {
    return JSON.parse(text);
  } catch (error) {
    return text;
  }
}

function createHttpError(response, payload) {
  const error = new Error(response.statusText || "Request gagal diproses.");
  error.response = {
    status: response.status,
    data: payload
  };
  return error;
}

export function apiErrorMessage(error, fallback = "Layanan sedang bermasalah. Coba beberapa saat lagi.") {
  if (error?.response?.status === 504) {
    return "Analisis terlalu lama. Coba mode target spesifik atau CV PDF teks yang lebih ringkas.";
  }

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

import axios from "axios";

const STORAGE_KEYS = {
  access: "consulta_juridica_access",
  refresh: "consulta_juridica_refresh",
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export function getAccessToken() {
  return window.localStorage.getItem(STORAGE_KEYS.access);
}

export function getRefreshToken() {
  return window.localStorage.getItem(STORAGE_KEYS.refresh);
}

export function setTokens(tokens) {
  window.localStorage.setItem(STORAGE_KEYS.access, tokens.access);
  window.localStorage.setItem(STORAGE_KEYS.refresh, tokens.refresh);
}

export function clearTokens() {
  window.localStorage.removeItem(STORAGE_KEYS.access);
  window.localStorage.removeItem(STORAGE_KEYS.refresh);
}

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshPromise = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status !== 401 || originalRequest?._retry) {
      return Promise.reject(error);
    }

    const refresh = getRefreshToken();
    if (!refresh) {
      clearTokens();
      return Promise.reject(error);
    }

    originalRequest._retry = true;
    if (!refreshPromise) {
      refreshPromise = axios
        .post(`${API_BASE_URL}/auth/refresh/`, { refresh })
        .then((response) => {
          const nextTokens = {
            access: response.data.access,
            refresh,
          };
          setTokens(nextTokens);
          return nextTokens;
        })
        .catch((refreshError) => {
          clearTokens();
          throw refreshError;
        })
        .finally(() => {
          refreshPromise = null;
        });
    }

    const nextTokens = await refreshPromise;
    originalRequest.headers.Authorization = `Bearer ${nextTokens.access}`;
    return api(originalRequest);
  },
);

export { api, API_BASE_URL };

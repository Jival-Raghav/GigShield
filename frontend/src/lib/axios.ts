import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const RAW_API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

function normalizeApiBaseUrl(baseUrl: string): string {
  const trimmed = baseUrl.trim().replace(/\/+$/, '');
  if (/\/api\/v1$/i.test(trimmed)) {
    return trimmed;
  }
  return `${trimmed}/api/v1`;
}

const API_BASE_URL = normalizeApiBaseUrl(RAW_API_BASE_URL);
const AUTH_STORAGE_KEYS = ['access_token', 'worker_id', 'expires_at', 'is_admin', 'worker_name', 'worker_phone'] as const;

type AuthStorageKey = (typeof AUTH_STORAGE_KEYS)[number];

function getSessionStorageSafe(): Storage | null {
  if (typeof window === 'undefined') {
    return null;
  }
  return window.sessionStorage;
}

function getLegacyLocalStorageSafe(): Storage | null {
  if (typeof window === 'undefined') {
    return null;
  }
  return window.localStorage;
}

function getAuthValue(key: AuthStorageKey): string | null {
  const session = getSessionStorageSafe();
  if (!session) {
    return null;
  }

  const sessionValue = session.getItem(key);
  if (sessionValue) {
    return sessionValue;
  }

  // Migrate legacy auth values so existing logins continue to work.
  const legacy = getLegacyLocalStorageSafe();
  const legacyValue = legacy?.getItem(key) ?? null;
  if (legacyValue) {
    session.setItem(key, legacyValue);
    legacy?.removeItem(key);
    return legacyValue;
  }

  return null;
}

function setAuthValue(key: AuthStorageKey, value: string): void {
  const session = getSessionStorageSafe();
  session?.setItem(key, value);
  // Remove legacy copy to avoid cross-tab token collisions.
  getLegacyLocalStorageSafe()?.removeItem(key);
}

function removeAuthValue(key: AuthStorageKey): void {
  getSessionStorageSafe()?.removeItem(key);
  getLegacyLocalStorageSafe()?.removeItem(key);
}

function clearAuthStorageValues(): void {
  AUTH_STORAGE_KEYS.forEach((key) => removeAuthValue(key));
}

// Create axios instance
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 100000,
});

// Request interceptor to attach auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      const token = getAuthValue('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (typeof window !== 'undefined') {
      // Handle 401 - token expired or invalid
      if (error.response?.status === 401) {
        clearAuthStorageValues();
        
        // Redirect to login if not already there
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

// Auth helpers
export const setAuthToken = (token: string): void => {
  setAuthValue('access_token', token);
};

export const getAuthToken = (): string | null => {
  return getAuthValue('access_token');
};

export const clearAuth = (): void => {
  clearAuthStorageValues();
};

export const isTokenExpired = (): boolean => {
  const expiresAt = getAuthValue('expires_at');
  if (!expiresAt) return true;
  return new Date(expiresAt) <= new Date();
};

export const setAuthSession = (payload: {
  access_token: string;
  worker_id: string;
  expires_at: string;
  is_admin: boolean;
  worker_name: string;
  worker_phone: string;
}): void => {
  setAuthValue('access_token', payload.access_token);
  setAuthValue('worker_id', payload.worker_id);
  setAuthValue('expires_at', payload.expires_at);
  setAuthValue('is_admin', payload.is_admin ? 'true' : 'false');
  setAuthValue('worker_name', payload.worker_name);
  setAuthValue('worker_phone', payload.worker_phone);
};

export const getAuthSession = (): {
  accessToken: string | null;
  workerId: string | null;
  expiresAt: string | null;
  isAdmin: boolean;
  workerName: string | null;
  workerPhone: string | null;
} => {
  const isAdminRaw = getAuthValue('is_admin');
  return {
    accessToken: getAuthValue('access_token'),
    workerId: getAuthValue('worker_id'),
    expiresAt: getAuthValue('expires_at'),
    isAdmin: isAdminRaw === 'true',
    workerName: getAuthValue('worker_name'),
    workerPhone: getAuthValue('worker_phone'),
  };
};

export default api;

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// Create axios instance
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor to attach auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
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
        localStorage.removeItem('access_token');
        localStorage.removeItem('worker_id');
        localStorage.removeItem('expires_at');
        localStorage.removeItem('is_admin');
        
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
  if (typeof window !== 'undefined') {
    localStorage.setItem('access_token', token);
  }
};

export const getAuthToken = (): string | null => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('access_token');
  }
  return null;
};

export const clearAuth = (): void => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('access_token');
    localStorage.removeItem('worker_id');
    localStorage.removeItem('expires_at');
    localStorage.removeItem('is_admin');
  }
};

export const isTokenExpired = (): boolean => {
  if (typeof window !== 'undefined') {
    const expiresAt = localStorage.getItem('expires_at');
    if (!expiresAt) return true;
    return new Date(expiresAt) <= new Date();
  }
  return true;
};

export default api;

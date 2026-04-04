'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { authApi, workersApi } from '@/lib/api';
import { clearAuth, isTokenExpired } from '@/lib/axios';
import type { Worker, LoginResponse } from '@/types';

interface AuthState {
  isAuthenticated: boolean;
  isAdmin: boolean;
  isLoading: boolean;
  worker: Worker | null;
  workerId: string | null;
}

interface AuthContextType extends AuthState {
  login: (phone: string, otp: string) => Promise<LoginResponse>;
  logout: () => void;
  refreshWorker: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    isAdmin: false,
    isLoading: true,
    worker: null,
    workerId: null,
  });

  // Check auth status on mount
  useEffect(() => {
    const checkAuth = async () => {
      if (typeof window === 'undefined') return;

      const token = localStorage.getItem('access_token');
      const workerId = localStorage.getItem('worker_id');
      const expiresAt = localStorage.getItem('expires_at');
      const isAdmin = localStorage.getItem('is_admin') === 'true';

      if (!token || !workerId || !expiresAt) {
        setState({ isAuthenticated: false, isAdmin: false, isLoading: false, worker: null, workerId: null });
        return;
      }

      // Check if token is expired
      if (isTokenExpired()) {
        clearAuth();
        setState({ isAuthenticated: false, isAdmin: false, isLoading: false, worker: null, workerId: null });
        return;
      }

      try {
        const worker = await workersApi.getById(workerId);
        setState({
          isAuthenticated: true,
          isAdmin,
          isLoading: false,
          worker,
          workerId,
        });
      } catch {
        clearAuth();
        setState({ isAuthenticated: false, isAdmin: false, isLoading: false, worker: null, workerId: null });
      }
    };

    checkAuth();
  }, []);

  const login = useCallback(async (phone: string, otp: string): Promise<LoginResponse> => {
    const response = await authApi.verifyOtp({ phone, otp });

    // Store auth data
    localStorage.setItem('access_token', response.access_token);
    localStorage.setItem('worker_id', response.worker_id);
    localStorage.setItem('expires_at', response.expires_at);
    localStorage.setItem('is_admin', response.is_admin ? 'true' : 'false');

    // Fetch worker details
    const worker = await workersApi.getById(response.worker_id);

    setState({
      isAuthenticated: true,
      isAdmin: response.is_admin,
      isLoading: false,
      worker,
      workerId: response.worker_id,
    });

    return response;
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    setState({
      isAuthenticated: false,
      isAdmin: false,
      isLoading: false,
      worker: null,
      workerId: null,
    });
    router.push('/login');
  }, [router]);

  const refreshWorker = useCallback(async () => {
    if (!state.workerId) return;
    
    try {
      const worker = await workersApi.getById(state.workerId);
      setState((prev) => ({ ...prev, worker }));
    } catch (error) {
      console.error('Failed to refresh worker:', error);
    }
  }, [state.workerId]);

  return (
    <AuthContext.Provider value={{ ...state, login, logout, refreshWorker }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { authApi, workersApi } from '@/lib/api';
import { clearAuth, getAuthSession, isTokenExpired, setAuthSession } from '@/lib/axios';
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

      const session = getAuthSession();
      const token = session.accessToken;
      const workerId = session.workerId;
      const expiresAt = session.expiresAt;
      const isAdmin = session.isAdmin;
      const workerName = session.workerName;
      const workerPhone = session.workerPhone;

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
        if (isAdmin) {
          setState({
            isAuthenticated: true,
            isAdmin: true,
            isLoading: false,
            worker: {
              id: workerId,
              name: workerName || 'Admin',
              phone: workerPhone || '',
              upi_id: null,
              platform: 'swiggy',
              vehicle_type: 'other',
              micro_zone_id: 'ADMIN',
              tenure_weeks: 0,
              avg_weekly_income: 0,
              trust_score: 1,
              cold_start: false,
              created_at: new Date(0).toISOString(),
              updated_at: new Date(0).toISOString(),
            },
            workerId,
          });
          return;
        }

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

    // Store auth per tab so admin/user sessions can run side-by-side.
    setAuthSession({
      access_token: response.access_token,
      worker_id: response.worker_id,
      expires_at: response.expires_at,
      is_admin: response.is_admin,
      worker_name: response.display_name,
      worker_phone: response.phone,
    });

    if (response.is_admin) {
      setState({
        isAuthenticated: true,
        isAdmin: true,
        isLoading: false,
        worker: {
          id: response.worker_id,
          name: response.display_name,
          phone: response.phone,
          upi_id: null,
          platform: 'swiggy',
          vehicle_type: 'other',
          micro_zone_id: 'ADMIN',
          tenure_weeks: 0,
          avg_weekly_income: 0,
          trust_score: 1,
          cold_start: false,
          created_at: new Date(0).toISOString(),
          updated_at: new Date(0).toISOString(),
        },
        workerId: response.worker_id,
      });
      return response;
    }

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
    if (!state.workerId || state.isAdmin) return;
    
    try {
      const worker = await workersApi.getById(state.workerId);
      setState((prev) => ({ ...prev, worker }));
    } catch (error) {
      console.error('Failed to refresh worker:', error);
    }
  }, [state.workerId]);

  const sendPeriodicLocationTrace = useCallback(() => {
    if (typeof window === 'undefined' || !state.isAuthenticated || state.isAdmin) {
      return;
    }
    if (!navigator.geolocation) {
      return;
    }

    if (navigator.permissions && navigator.permissions.query) {
      navigator.permissions.query({ name: 'geolocation' }).then((permissionStatus) => {
        if (permissionStatus.state !== 'granted') {
          return;
        }

        navigator.geolocation.getCurrentPosition(
          async (position) => {
            try {
              await workersApi.addLocationTrace({
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                accuracy_meters: position.coords.accuracy,
                source: 'browser_periodic',
              });
            } catch {
              // Silent failure keeps auth/session flow unaffected.
            }
          },
          () => {
            // Permission denied or unavailable GPS should not break app usage.
          },
          {
            enableHighAccuracy: true,
            timeout: 8000,
            maximumAge: 5 * 60 * 1000,
          }
        );
      }).catch(() => {
        // If permissions are unavailable, do not prompt in the background.
      });
      return;
    }

    // Without explicit permission state, avoid prompting the user in the background.
  }, [state.isAuthenticated, state.isAdmin]);

  useEffect(() => {
    if (!state.isAuthenticated) {
      return;
    }

    sendPeriodicLocationTrace();
    const intervalId = window.setInterval(sendPeriodicLocationTrace, 30 * 60 * 1000);

    return () => window.clearInterval(intervalId);
  }, [state.isAuthenticated, sendPeriodicLocationTrace]);

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

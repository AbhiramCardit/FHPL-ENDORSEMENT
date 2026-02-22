import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';

import apiClient, { type LoginRequestPayload } from '@/lib/api-client';

import { clearStoredAccessToken, readStoredAccessToken, writeStoredAccessToken } from './auth-storage';
import { AuthContext } from './auth-context';
import type { AuthContextValue, AuthState, LoginCredentials } from './auth-types';

function createUnauthenticatedState(): AuthState {
  return {
    status: 'unauthenticated',
    user: null,
    token: null,
  };
}

const INITIAL_AUTH_STATE: AuthState = {
  status: 'loading',
  user: null,
  token: null,
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authState, setAuthState] = useState<AuthState>(INITIAL_AUTH_STATE);

  const logout = useCallback(() => {
    clearStoredAccessToken();
    apiClient.clearToken();
    setAuthState(createUnauthenticatedState());
  }, []);

  const login = useCallback(async (credentials: LoginCredentials) => {
    const payload: LoginRequestPayload = {
      username: credentials.email,
      password: credentials.password,
    };

    const tokenResponse = await apiClient.login(payload);
    const accessToken = tokenResponse.access_token;

    writeStoredAccessToken(accessToken);
    apiClient.setToken(accessToken);

    try {
      const user = await apiClient.getCurrentUser();
      setAuthState({
        status: 'authenticated',
        user,
        token: accessToken,
      });
    } catch (error) {
      clearStoredAccessToken();
      apiClient.clearToken();
      setAuthState(createUnauthenticatedState());
      throw error;
    }
  }, []);

  useEffect(() => {
    apiClient.setUnauthorizedHandler(() => {
      logout();
    });

    return () => {
      apiClient.setUnauthorizedHandler(null);
    };
  }, [logout]);

  useEffect(() => {
    let cancelled = false;

    const initializeAuth = async () => {
      const storedToken = readStoredAccessToken();

      if (!storedToken) {
        apiClient.clearToken();
        if (!cancelled) {
          setAuthState(createUnauthenticatedState());
        }
        return;
      }

      apiClient.setToken(storedToken);

      try {
        const user = await apiClient.getCurrentUser();
        if (!cancelled) {
          setAuthState({
            status: 'authenticated',
            user,
            token: storedToken,
          });
        }
      } catch {
        clearStoredAccessToken();
        apiClient.clearToken();
        if (!cancelled) {
          setAuthState(createUnauthenticatedState());
        }
      }
    };

    void initializeAuth();

    return () => {
      cancelled = true;
    };
  }, []);

  const contextValue = useMemo<AuthContextValue>(
    () => ({
      status: authState.status,
      user: authState.user,
      isAuthenticated: authState.status === 'authenticated',
      login,
      logout,
    }),
    [authState.status, authState.user, login, logout],
  );

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
}

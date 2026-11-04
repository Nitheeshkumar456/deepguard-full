import React, { createContext, useContext, useState, useEffect } from "react";
import { apiService, ApiError } from "../services/api";
import { syncWebSocket } from "../services/websocket";

interface UserProfile {
  id: number;
  name: string;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

interface AuthContextType {
  user: UserProfile | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshProfile = async () => {
    try {
      const data = await apiService.getMe();
      setUser(data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        // Attempt to auto-refresh session if access token expired
        try {
          await apiService.refresh();
          const retryData = await apiService.getMe();
          setUser(retryData);
          return;
        } catch (refreshErr) {
          console.warn("Session auto-refresh failed. Clearing session.", refreshErr);
        }
      }
      setUser(null);
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    }
  };

  useEffect(() => {
    const initializeAuth = async () => {
      const token = localStorage.getItem("access_token");
      if (token) {
        await refreshProfile();
        syncWebSocket.connect();
      }
      setLoading(false);
    };
    initializeAuth();

    // Listen to real-time profile updates from Android or other sessions
    const unsubProfile = syncWebSocket.subscribe("profile.updated", (updatedUser) => {
      if (updatedUser) {
        setUser((prev) => (prev ? { ...prev, ...updatedUser } : updatedUser));
      }
    });

    const unsubReconnect = syncWebSocket.onReconnect(() => {
      refreshProfile();
    });

    return () => {
      unsubProfile();
      unsubReconnect();
    };
  }, []);

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      await apiService.login(email, password);
      await refreshProfile();
      syncWebSocket.connect();
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      syncWebSocket.disconnect();
      await apiService.logout();
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const value: AuthContextType = {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    logout,
    refreshProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

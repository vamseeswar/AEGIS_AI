"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { getValidAuthToken } from "@/lib/auth-token";

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  organization_id: string;
  organization_name: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    fullName: string,
    organizationName: string
  ) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchProfile = async () => {
    let token = localStorage.getItem("aegis_access_token");
    if (!token) {
      token = await getValidAuthToken();
    }

    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const profile = await api.get<User>("/api/v1/auth/me");
      setUser(profile);
    } catch {
      // If token is invalid or expired, try auto-login refresh once
      try {
        await getValidAuthToken(true);
        const profile = await api.get<User>("/api/v1/auth/me");
        setUser(profile);
      } catch {
        localStorage.removeItem("aegis_access_token");
        localStorage.removeItem("aegis_refresh_token");
        setUser(null);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();

    const handleAuthUpdated = () => {
      fetchProfile();
    };
    window.addEventListener("aegis_auth_updated", handleAuthUpdated);
    return () => {
      window.removeEventListener("aegis_auth_updated", handleAuthUpdated);
    };
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const tokens = await api.post<{
        access_token: string;
        refresh_token: string;
        token_type: string;
      }>("/api/v1/auth/login", { email, password });

      localStorage.setItem("aegis_access_token", tokens.access_token);
      localStorage.setItem("aegis_refresh_token", tokens.refresh_token);

      const profile = await api.get<User>("/api/v1/auth/me");
      setUser(profile);
    } catch (err) {
      setIsLoading(false);
      throw err;
    }
    setIsLoading(false);
  };

  const register = async (
    email: string,
    password: string,
    fullName: string,
    organizationName: string
  ) => {
    setIsLoading(true);
    try {
      await api.post<User>("/api/v1/auth/register", {
        email,
        password,
        full_name: fullName,
        organization_name: organizationName,
      });

      // Auto login after registration
      await login(email, password);
    } catch (err) {
      setIsLoading(false);
      throw err;
    }
  };

  const logout = () => {
    try {
      api.post("/api/v1/auth/logout").catch(() => {});
    } finally {
      localStorage.removeItem("aegis_access_token");
      localStorage.removeItem("aegis_refresh_token");
      setUser(null);
      window.location.href = "/login";
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        refreshUser: fetchProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

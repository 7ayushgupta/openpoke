'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';

interface User {
  id: string;
  email: string;
  provider: string;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: () => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Get API base URL - must match the Python backend server
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8001';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!user;

  // Check for existing token on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const token = localStorage.getItem('openpoke_token');
        if (!token) {
          setIsLoading(false);
          return;
        }

        const response = await fetch(`${API_BASE}/api/v1/auth/me`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
        } else {
          // Token is invalid, remove it
          localStorage.removeItem('openpoke_token');
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('openpoke_token');
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/v1/auth/login`);
      if (!resp.ok) throw new Error('Failed to init login');
      const data = await resp.json();
      const url = (data && (data.auth_url || data.authorization_url)) as string | undefined;
      if (url) {
        window.location.href = url;
      }
    } catch (e) {
      console.error('Login init failed', e);
    }
  }, []);

  const logout = useCallback(() => {
    // Clear local state and token
    setUser(null);
    localStorage.removeItem('openpoke_token');
    
    // Call logout endpoint (optional)
    fetch(`${API_BASE}/api/v1/auth/logout`, { method: 'POST' }).catch(console.error);
  }, []);

  // OAuth callback is handled in /auth/callback

  const value: AuthContextType = {
    user,
    isLoading,
    login,
    logout,
    isAuthenticated,
  };

  return (
    <AuthContext.Provider value={value}>
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


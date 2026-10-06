import React, {
  createContext,
  useContext,
  useState,
  useEffect,
} from 'react';

import type { User } from '../types';

import {
  apiGetMe,
  apiLogin,
  apiRegister,
  getStoredToken,
  setStoredToken,
  clearStoredToken,
} from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    name: string,
    email: string,
    password: string
  ) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(
  undefined
);

export const AuthProvider: React.FC<{
  children: React.ReactNode;
}> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);

  const [token, setToken] = useState<string | null>(
    getStoredToken()
  );

  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const initAuth = async () => {
      const stored = getStoredToken();

      if (stored) {
        try {
          const userData = await apiGetMe();

          setUser(userData);
          setToken(stored);
        } catch (error) {
          console.error('Authentication initialization failed:', error);

          clearStoredToken();
          setToken(null);
          setUser(null);
        }
      }

      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (
    email: string,
    password: string
  ): Promise<void> => {
    const data = await apiLogin(email, password);

    setStoredToken(data.access_token);
    setToken(data.access_token);
    setUser(data.user);
  };

  const register = async (
    name: string,
    email: string,
    password: string
  ): Promise<void> => {
    const data = await apiRegister(
      name,
      email,
      password
    );

    setStoredToken(data.access_token);
    setToken(data.access_token);
    setUser(data.user);
  };

  const logout = (): void => {
    clearStoredToken();

    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      'useAuth must be used within an AuthProvider'
    );
  }

  return context;
};
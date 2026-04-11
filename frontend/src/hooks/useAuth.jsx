import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { authService } from "../services/auth";
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const bootstrap = async () => {
      const access = getAccessToken();
      const refresh = getRefreshToken();
      if (!access || !refresh) {
        setLoading(false);
        return;
      }

      try {
        const currentUser = await authService.me();
        setUser(currentUser);
      } catch (error) {
        clearTokens();
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    bootstrap();
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      async login(username, password) {
        const tokens = await authService.login(username, password);
        setTokens(tokens);
        const currentUser = await authService.me();
        setUser(currentUser);
        return currentUser;
      },
      logout() {
        clearTokens();
        setUser(null);
      },
    }),
    [loading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}

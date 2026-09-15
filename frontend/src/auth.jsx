import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, clearSession, getSession, setSession } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setLocal] = useState(() => getSession());
  const [error, setError] = useState("");

  useEffect(() => {
    const existing = getSession();
    if (!existing?.user?.id) return;
    api
      .me()
      .then((payload) => {
        setSession(payload);
        setLocal(payload);
      })
      .catch(() => {
        clearSession();
        setLocal(null);
      });
  }, []);

  const value = useMemo(
    () => ({
      session,
      error,
      applySession(payload) {
        setSession(payload);
        setLocal(payload);
      },
      logout() {
        clearSession();
        setLocal(null);
      },
      async refresh() {
        if (!getSession()?.user?.id) return;
        const payload = await api.me();
        setSession(payload);
        setLocal(payload);
      },
    }),
    [session, error]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

export function roleHome(role) {
  if (role === "doctor") return "/doctor";
  if (role === "surrogate") return "/surrogate";
  return "/patient";
}

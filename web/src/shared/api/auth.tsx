import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { UserManager } from "oidc-client-ts";
import { config } from "../config";

export type AuthStatus = "demo" | "unconfigured" | "anonymous" | "authenticated";

interface AuthValue {
  status: AuthStatus;
  token: string | null;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

type Manager = UserManager;

/**
 * Sign-in uses the OIDC authorization code flow with PKCE. The access token is
 * held in memory only: nothing is written to localStorage or cookies, so there
 * is no stored credential to steal. Reloading the page signs the user out.
 */
async function createManager(): Promise<Manager> {
  const { UserManager, WebStorageStateStore, InMemoryWebStorage } = await import("oidc-client-ts");
  return new UserManager({
    authority: config.oidcAuthority,
    client_id: config.oidcClientId,
    redirect_uri: `${window.location.origin}/auth/callback`,
    post_logout_redirect_uri: window.location.origin,
    response_type: "code",
    scope: "openid prices:read members:read insights:read insights:write",
    userStore: new WebStorageStateStore({ store: new InMemoryWebStorage() }),
    stateStore: new WebStorageStateStore({ store: window.sessionStorage }),
  });
}

function initialStatus(): AuthStatus {
  if (config.demoMode) return "demo";
  if (config.devToken) return "authenticated";
  return config.oidcAuthority ? "anonymous" : "unconfigured";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>(initialStatus);
  const [token, setToken] = useState<string | null>(config.devToken || null);
  const [manager, setManager] = useState<Manager | null>(null);

  useEffect(() => {
    if (status !== "anonymous") return;
    const controller = new AbortController();
    void (async () => {
      const m = await createManager();
      if (controller.signal.aborted) return;
      setManager(m);
      if (window.location.pathname === "/auth/callback") {
        const user = await m.signinRedirectCallback();
        setToken(user.access_token);
        setStatus("authenticated");
        window.history.replaceState({}, "", "/");
      }
    })();
    return () => { controller.abort(); };
  }, [status]);

  const signIn = useCallback(async () => {
    const m = manager ?? (await createManager());
    await m.signinRedirect();
  }, [manager]);

  const signOut = useCallback(async () => {
    setToken(null);
    setStatus(config.oidcAuthority ? "anonymous" : "unconfigured");
    await manager?.signoutRedirect();
  }, [manager]);

  const value = useMemo(() => ({ status, token, signIn, signOut }), [status, token, signIn, signOut]);
  return <AuthContext value={value}>{children}</AuthContext>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}

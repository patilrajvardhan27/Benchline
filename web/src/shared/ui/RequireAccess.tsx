import type { ReactNode } from "react";
import { useAuth } from "../api/auth";

/** Gate for pages whose API needs a signed-in user. Demo snapshots are open. */
export function RequireAccess({ children }: { children: ReactNode }) {
  const { status, signIn } = useAuth();
  if (status === "demo" || status === "authenticated") return <>{children}</>;
  if (status === "unconfigured") {
    return (
      <div className="banner" role="note">
        <p><strong>Sign-in is not set up for this deployment.</strong> This page needs a signed-in user.</p>
      </div>
    );
  }
  return (
    <div className="panel">
      <h2>Sign in to continue</h2>
      <p>This page shows data that needs an account.</p>
      <button type="button" className="btn" onClick={() => void signIn()}>Sign in</button>
    </div>
  );
}

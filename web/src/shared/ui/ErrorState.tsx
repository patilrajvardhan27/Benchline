import { ApiError } from "../api/errors";
import { useAuth } from "../api/auth";

interface Props {
  error: unknown;
  onRetry?: () => void;
}

/** Shows plain-language failure text. Raw error objects are never rendered. */
export function ErrorState({ error, onRetry }: Props) {
  const { signIn, status } = useAuth();
  const apiError = error instanceof ApiError ? error : null;
  const message = apiError?.message ?? "Something went wrong. Please try again.";
  const needsSignIn = apiError?.status === 401 && status === "anonymous";
  return (
    <div className="banner" role="alert">
      <p>
        <strong>{message}</strong>
      </p>
      <div className="cluster" style={{ marginTop: "var(--bl-space-3)" }}>
        {needsSignIn && (
          <button type="button" className="btn" onClick={() => void signIn()}>Sign in</button>
        )}
        {onRetry && (
          <button type="button" className="btn btn--quiet" onClick={onRetry}>Try again</button>
        )}
      </div>
    </div>
  );
}

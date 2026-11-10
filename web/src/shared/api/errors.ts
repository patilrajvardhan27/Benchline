/** A failed API call. The message is safe to show: it never carries server internals. */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const FRIENDLY: Record<number, string> = {
  401: "You need to sign in to see this.",
  403: "Your account does not have access to this.",
  404: "We could not find what you asked for.",
  429: "Too many requests. Please wait a moment and try again.",
};

/** Maps a status to words for people. Server detail text is deliberately ignored. */
export function messageForStatus(status: number): string {
  return FRIENDLY[status] ?? (status >= 500
    ? "The service had a problem. Please try again shortly."
    : "The request could not be completed.");
}

import { config } from "../config";
import { demoGet } from "./demo";
import { ApiError, messageForStatus } from "./errors";
import { type QueryParams, toQueryString } from "./query";

export interface RequestOptions {
  query?: QueryParams;
  token?: string | null;
  signal?: AbortSignal;
}

async function send(method: string, url: string, token?: string | null, body?: unknown, signal?: AbortSignal) {
  const headers: Record<string, string> = { Accept: "application/json, application/problem+json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  try {
    return await fetch(url, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
      credentials: "omit", // bearer tokens only, so cookies are never attached
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(0, "The service could not be reached. Check your connection and try again.");
  }
}

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) throw new ApiError(response.status, messageForStatus(response.status));
  return (await response.json()) as T;
}

export async function apiGet<T>(path: string, options: RequestOptions = {}): Promise<T> {
  if (config.demoMode) return demoGet<T>(path, options.query, options.signal);
  const url = `${config.apiBaseUrl}${path}${toQueryString(options.query)}`;
  return parse<T>(await send("GET", url, options.token, undefined, options.signal));
}

export async function apiPatch<T>(path: string, body: unknown, options: RequestOptions = {}): Promise<T> {
  if (config.demoMode) {
    throw new ApiError(403, "Reviews are turned off in the public demo snapshot.");
  }
  const url = `${config.apiBaseUrl}${path}`;
  return parse<T>(await send("PATCH", url, options.token, body, options.signal));
}

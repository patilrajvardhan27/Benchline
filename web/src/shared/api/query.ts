export type QueryParams = Record<string, string | number | undefined>;

/** Builds "?a=1&b=2", skipping empty values so URLs stay clean and cache keys stable. */
export function toQueryString(params?: QueryParams): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

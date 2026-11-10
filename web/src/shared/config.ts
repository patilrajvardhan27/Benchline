import { z } from "zod";

const schema = z.object({
  VITE_API_BASE_URL: z.string().default(""),
  VITE_DEMO_MODE: z.string().default("false"),
  VITE_CONTACT_EMAIL: z.string().default("contact@example.com"),
  VITE_OPERATOR_NAME: z.string().default("Benchline maintainer"),
  VITE_OIDC_AUTHORITY: z.string().default(""),
  VITE_OIDC_CLIENT_ID: z.string().default("benchline-web"),
  VITE_DEV_TOKEN: z.string().default(""),
});

// Each variable is named one by one. Passing the whole `import.meta.env` object would make Vite
// copy every VITE_ value into the bundle, including ones this file never reads.
const env = schema.parse({
  VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
  VITE_DEMO_MODE: import.meta.env.VITE_DEMO_MODE,
  VITE_CONTACT_EMAIL: import.meta.env.VITE_CONTACT_EMAIL,
  VITE_OPERATOR_NAME: import.meta.env.VITE_OPERATOR_NAME,
  VITE_OIDC_AUTHORITY: import.meta.env.VITE_OIDC_AUTHORITY,
  VITE_OIDC_CLIENT_ID: import.meta.env.VITE_OIDC_CLIENT_ID,
  // Read only in development. In a production build `import.meta.env.DEV` is false and the
  // whole expression is removed, so a token can never end up in the shipped bundle.
  VITE_DEV_TOKEN: import.meta.env.DEV ? import.meta.env.VITE_DEV_TOKEN : undefined,
});

/** Public, build-time settings. Nothing secret belongs here: it ships to every browser. */
export const config = {
  apiBaseUrl: env.VITE_API_BASE_URL.replace(/\/$/, ""),
  demoMode: env.VITE_DEMO_MODE === "true",
  contactEmail: env.VITE_CONTACT_EMAIL,
  operatorName: env.VITE_OPERATOR_NAME,
  oidcAuthority: env.VITE_OIDC_AUTHORITY,
  oidcClientId: env.VITE_OIDC_CLIENT_ID,
  devToken: env.VITE_DEV_TOKEN,
  legalUpdated: "9 November 2026",
} as const;

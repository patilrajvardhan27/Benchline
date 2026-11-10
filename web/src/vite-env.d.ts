/// <reference types="vite/client" />

// The only build-time variables the app reads. Declaring them gives `import.meta.env.VITE_*` real types.
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_DEMO_MODE?: string;
  readonly VITE_CONTACT_EMAIL?: string;
  readonly VITE_OPERATOR_NAME?: string;
  readonly VITE_OIDC_AUTHORITY?: string;
  readonly VITE_OIDC_CLIENT_ID?: string;
  readonly VITE_DEV_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

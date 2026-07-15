/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Override the local API base URL (defaults to http://127.0.0.1:8787). */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

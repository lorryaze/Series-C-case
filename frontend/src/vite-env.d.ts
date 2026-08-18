/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the platform API; defaults to the dev-server proxy at ``/api``. */
  readonly VITE_API_BASE_URL?: string;
  /** Absolute URL of the FastAPI Swagger UI, linked from the sidebar. */
  readonly VITE_API_DOCS_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

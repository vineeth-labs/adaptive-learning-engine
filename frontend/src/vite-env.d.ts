/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_USE_MOCKS?: string;
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_USER_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

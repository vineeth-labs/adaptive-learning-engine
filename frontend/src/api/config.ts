// Runtime configuration sourced from Vite env vars (see .env.example).

export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== "false";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

// In live mode this must be a real user UUID present in the backend DB.
export const USER_ID =
  import.meta.env.VITE_USER_ID ?? "00000000-0000-0000-0000-000000000001";

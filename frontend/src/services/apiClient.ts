/**
 * Thin fetch wrapper shared by every tool: injects the bearer token, unwraps the
 * platform error envelope and, on a 401, tries the refresh token once before
 * dropping the session.
 */

const TOKEN_STORAGE_KEY = 'internal-tools.token';
const REFRESH_TOKEN_STORAGE_KEY = 'internal-tools.refresh-token';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
    request_id: string | null;
  };
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details: Record<string, unknown>) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }

  get isForbidden(): boolean {
    return this.status === 403;
  }
}

export const tokenStorage = {
  read(): string | null {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  },
  write(token: string): void {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  },
  readRefresh(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY);
  },
  writeRefresh(token: string): void {
    localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token);
  },
  clear(): void {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
  },
};

type SessionExpiredListener = () => void;

const sessionExpiredListeners = new Set<SessionExpiredListener>();

/**
 * Notified when the session is dropped mid-flight (both tokens are gone), so the
 * shell can clear the cached user and route to the login page without a reload.
 */
export function onSessionExpired(listener: SessionExpiredListener): () => void {
  sessionExpiredListeners.add(listener);
  return () => sessionExpiredListeners.delete(listener);
}

export type QueryParams = Record<string, string | number | boolean | undefined | null>;

export function buildQuery(params: QueryParams = {}): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value));
    }
  });
  const query = search.toString();
  return query ? `?${query}` : '';
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  params?: QueryParams;
}

async function parseError(response: Response): Promise<ApiError> {
  let code = 'http_error';
  let message = response.statusText || 'Request failed';
  let details: Record<string, unknown> = {};
  try {
    const body = (await response.json()) as Partial<ApiErrorBody>;
    if (body.error) {
      code = body.error.code;
      message = body.error.message;
      details = body.error.details ?? {};
    }
  } catch {
    // Non-JSON error bodies fall back to the status text.
  }
  return new ApiError(response.status, code, message, details);
}

/** Paths where a 401 is the answer, not a stale-token symptom. */
const NON_REFRESHABLE_PATHS = ['/auth/login', '/auth/refresh'];

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

/** In-flight refresh, so parallel 401s wait on a single rotation. */
let refreshInFlight: Promise<boolean> | null = null;

async function rotateTokens(): Promise<boolean> {
  const refreshToken = tokenStorage.readRefresh();
  if (!refreshToken) return false;

  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) return false;

  const pair = (await response.json()) as TokenPair;
  tokenStorage.write(pair.access_token);
  tokenStorage.writeRefresh(pair.refresh_token);
  return true;
}

async function refreshSession(): Promise<boolean> {
  refreshInFlight ??= rotateTokens()
    .catch(() => false)
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
}

function send(path: string, options: RequestOptions): Promise<Response> {
  const { method = 'GET', body, params } = options;
  const token = tokenStorage.read();
  return fetch(`${API_BASE_URL}${path}${buildQuery(params)}`, {
    method,
    headers: {
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response = await send(path, options);

  if (response.status === 401 && !NON_REFRESHABLE_PATHS.includes(path)) {
    // One retry only: a second 401 means the refresh token is gone too.
    if (await refreshSession()) {
      response = await send(path, options);
    }
  }

  if (response.status === 401) {
    tokenStorage.clear();
    if (!NON_REFRESHABLE_PATHS.includes(path)) {
      // The credentials are unusable: tell the shell so it routes to /login
      // instead of rendering empty data behind a stale user.
      sessionExpiredListeners.forEach((listener) => listener());
    }
    throw await parseError(response);
  }
  if (!response.ok) {
    throw await parseError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

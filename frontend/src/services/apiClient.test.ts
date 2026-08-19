import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, buildQuery, onSessionExpired, request, tokenStorage } from './apiClient';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function unauthorized(): Response {
  return jsonResponse(
    {
      error: {
        code: 'authentication_error',
        message: 'Access token has expired',
        details: {},
        request_id: null,
      },
    },
    401,
  );
}

function authHeader(call: unknown[]): string | null {
  const init = call[1] as RequestInit;
  return new Headers(init.headers).get('Authorization');
}

describe('buildQuery', () => {
  it('drops empty values and encodes the rest', () => {
    expect(buildQuery({ page: 2, search: '', status: undefined, q: 'a b' })).toBe(
      '?page=2&q=a+b',
    );
    expect(buildQuery()).toBe('');
  });
});

describe('request', () => {
  beforeEach(() => {
    tokenStorage.write('access-1');
    tokenStorage.writeRefresh('refresh-1');
  });

  it('sends the stored bearer token', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(request('/kyc/reviews')).resolves.toEqual({ ok: true });
    expect(authHeader(fetchMock.mock.calls[0] as unknown[])).toBe('Bearer access-1');
  });

  it('refreshes once on a 401 and replays the original request', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(unauthorized())
      .mockResolvedValueOnce(
        jsonResponse({ access_token: 'access-2', refresh_token: 'refresh-2' }),
      )
      .mockResolvedValueOnce(jsonResponse({ items: [] }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(request('/refunds')).resolves.toEqual({ items: [] });

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1]?.[0]).toContain('/auth/refresh');
    expect(authHeader(fetchMock.mock.calls[2] as unknown[])).toBe('Bearer access-2');
    expect(tokenStorage.read()).toBe('access-2');
    expect(tokenStorage.readRefresh()).toBe('refresh-2');
  });

  it('clears the session when the refresh token is rejected', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(unauthorized())
      .mockResolvedValueOnce(unauthorized());
    vi.stubGlobal('fetch', fetchMock);

    await expect(request('/refunds')).rejects.toBeInstanceOf(ApiError);

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(tokenStorage.read()).toBeNull();
    expect(tokenStorage.readRefresh()).toBeNull();
  });

  it('announces the dead session so the shell can route to login', async () => {
    const listener = vi.fn();
    const unsubscribe = onSessionExpired(listener);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(unauthorized()));

    await expect(request('/refunds')).rejects.toBeInstanceOf(ApiError);
    expect(listener).toHaveBeenCalledTimes(1);

    unsubscribe();
    await expect(request('/refunds')).rejects.toBeInstanceOf(ApiError);
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it('does not announce an expired session for a rejected login', async () => {
    const listener = vi.fn();
    const unsubscribe = onSessionExpired(listener);
    tokenStorage.clear();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(unauthorized()));

    await expect(request('/auth/login', { method: 'POST' })).rejects.toBeInstanceOf(ApiError);
    expect(listener).not.toHaveBeenCalled();
    unsubscribe();
  });

  it('does not try to refresh a failed login', async () => {
    tokenStorage.clear();
    const fetchMock = vi.fn().mockResolvedValue(unauthorized());
    vi.stubGlobal('fetch', fetchMock);

    await expect(
      request('/auth/login', { method: 'POST', body: { email: 'a@b.c', password: 'x' } }),
    ).rejects.toMatchObject({ status: 401, code: 'authentication_error' });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('surfaces the platform error envelope', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            error: {
              code: 'rate_limited',
              message: 'Too many failed login attempts. Try again later.',
              details: { retry_after_seconds: 42 },
              request_id: 'abc',
            },
          },
          429,
        ),
      ),
    );

    const error = await request('/auth/login', { method: 'POST' }).catch((caught) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe('rate_limited');
    expect((error as ApiError).details).toEqual({ retry_after_seconds: 42 });
  });
});

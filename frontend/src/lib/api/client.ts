/**
 * Shared API client for PolarOps frontend.
 * - Uses fetch (no axios).
 * - Base URL from VITE_API_BASE_URL env var.
 * - Parses the ApiResponse envelope.
 * - Surfaces errors[] array from backend.
 * - Supports X-Request-ID and X-Actor-ID headers.
 * - Never silently swallows API errors.
 */

import type { ApiResponse } from '../types/api';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

export class ApiError extends Error {
  readonly code: string;
  readonly field?: string | null;
  readonly status?: number;

  constructor(
    code: string,
    message: string,
    field?: string | null,
    status?: number,
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.field = field;
    this.status = status;
  }
}

function correlationId(): string {
  return crypto.randomUUID();
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  actorId?: string;
  signal?: AbortSignal;
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = 'GET', body, actorId, signal } = options;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    'X-Request-ID': correlationId(),
  };
  if (actorId) headers['X-Actor-ID'] = actorId;

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (networkError) {
    throw new ApiError(
      'NETWORK_ERROR',
      `Network request failed: ${(networkError as Error).message}`,
    );
  }

  let envelope: ApiResponse<T>;
  try {
    envelope = (await response.json()) as ApiResponse<T>;
  } catch {
    throw new ApiError(
      'PARSE_ERROR',
      `Server returned non-JSON response (HTTP ${response.status})`,
      null,
      response.status,
    );
  }

  // Surface backend errors[]
  if (envelope.errors && envelope.errors.length > 0) {
    const first = envelope.errors[0];
    throw new ApiError(first.code, first.message, first.field, response.status);
  }

  if (!response.ok) {
    throw new ApiError(
      'HTTP_ERROR',
      `Request failed with status ${response.status}`,
      null,
      response.status,
    );
  }

  return envelope.data as T;
}

export const apiClient = {
  get: <T>(path: string, signal?: AbortSignal) =>
    request<T>(path, { method: 'GET', signal }),

  post: <T>(path: string, body: unknown, actorId?: string) =>
    request<T>(path, { method: 'POST', body, actorId }),

  patch: <T>(path: string, body: unknown, actorId?: string) =>
    request<T>(path, { method: 'PATCH', body, actorId }),

  delete: <T>(path: string, actorId?: string) =>
    request<T>(path, { method: 'DELETE', actorId }),
};

// Pagination helper
export function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') {
      q.set(k, String(v));
    }
  }
  const str = q.toString();
  return str ? `?${str}` : '';
}

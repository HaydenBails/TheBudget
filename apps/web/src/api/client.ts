// Typed local API client for the FastAPI backend. Local-first: the base URL
// defaults to loopback and can be overridden with VITE_API_BASE at build time.

// In a production build the app is served by the FastAPI backend on the same
// origin, so the API base is empty (relative). Under the Vite dev server the app
// runs on a different port, so it targets the local API explicitly. Either can be
// overridden with VITE_API_BASE at build time.
export const API_BASE = (
  (import.meta.env.VITE_API_BASE as string | undefined) ??
  (import.meta.env.DEV ? 'http://127.0.0.1:8787' : '')
).replace(/\/$/, '');

export interface FieldError {
  field: string;
  message: string;
}

/** Normalized error for all API failures, including field-specific validation. */
export class ApiError extends Error {
  readonly status: number;
  readonly fieldErrors: FieldError[];
  readonly code?: string;
  readonly importId?: number;
  readonly duplicateOfImportId?: number;
  readonly lifecycleStatus?: string;

  constructor(message: string, status: number, fieldErrors: FieldError[] = [], metadata: {
    code?: string;
    importId?: number;
    duplicateOfImportId?: number;
    lifecycleStatus?: string;
  } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.fieldErrors = fieldErrors;
    this.code = metadata.code;
    this.importId = metadata.importId;
    this.duplicateOfImportId = metadata.duplicateOfImportId;
    this.lifecycleStatus = metadata.lifecycleStatus;
  }

  /** Convenience: the message for a specific field, if any. */
  fieldError(field: string): string | undefined {
    return this.fieldErrors.find((f) => f.field === field)?.message;
  }
}

interface RawFieldError {
  field?: unknown;
  message?: unknown;
  loc?: unknown[];
  msg?: unknown;
}

async function toApiError(res: Response): Promise<ApiError> {
  let detail: unknown;
  let payload: Record<string, unknown> = {};
  try {
    payload = await res.json() as Record<string, unknown>;
    detail = payload.detail;
  } catch {
    /* non-JSON body */
  }
  // Contract shape: detail = [{ field, message }]. Also tolerate FastAPI's
  // default 422 shape: [{ loc: [...], msg }].
  if (Array.isArray(detail)) {
    const fields: FieldError[] = (detail as RawFieldError[]).map((d) => ({
      field: String(d.field ?? (Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : '') ?? ''),
      message: String(d.message ?? d.msg ?? 'Invalid value'),
    }));
    const summary = fields.map((f) => f.message).filter(Boolean).join('; ') || 'Validation error';
    return new ApiError(summary, res.status, fields);
  }
  const metadata = {
    code: typeof payload.code === 'string' ? payload.code : undefined,
    importId: typeof payload.import_id === 'number' ? payload.import_id : undefined,
    duplicateOfImportId: typeof payload.duplicate_of_import_id === 'number' ? payload.duplicate_of_import_id : undefined,
    lifecycleStatus: typeof payload.status === 'string' ? payload.status : undefined,
  };
  if (typeof detail === 'string') return new ApiError(detail, res.status, [], metadata);
  return new ApiError(`Request failed (${res.status})`, res.status, [], metadata);
}

async function request<T>(method: string, path: string, body?: unknown, form = false): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: body !== undefined && !form ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? (form ? body as FormData : JSON.stringify(body)) : undefined,
    });
  } catch {
    // Network failure / server unreachable / CORS — surface a clear offline error.
    throw new ApiError('Cannot reach the local API. Is the backend running?', 0);
  }
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  postForm: <T>(path: string, body: FormData) => request<T>('POST', path, body, true),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  delete: <T>(path: string) => request<T>('DELETE', path),
};

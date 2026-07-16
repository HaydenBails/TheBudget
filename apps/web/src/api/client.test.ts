import { afterEach, describe, expect, it, vi } from 'vitest';
import { API_BASE, ApiError, api } from './client';

function res(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

afterEach(() => vi.unstubAllGlobals());

describe('api client', () => {
  it('defaults the base URL to loopback', () => {
    expect(API_BASE).toContain('127.0.0.1');
  });

  it('returns parsed JSON on success', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => res(200, { hello: 'world' })));
    await expect(api.get('/x')).resolves.toEqual({ hello: 'world' });
  });

  it('sends PUT bodies and DELETE requests for replace and soft-delete endpoints', async () => {
    const fetchMock = vi.fn(async () => res(200, { ok: true }));
    vi.stubGlobal('fetch', fetchMock);
    await api.put('/x/splits', { splits: [] });
    await api.delete('/x');
    expect(fetchMock).toHaveBeenNthCalledWith(1, expect.stringContaining('/x/splits'), expect.objectContaining({ method: 'PUT', body: '{"splits":[]}' }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, expect.stringContaining('/x'), expect.objectContaining({ method: 'DELETE' }));
  });

  it('maps the contract field-error shape to ApiError', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => res(422, { detail: [{ field: 'name', message: 'Required' }] })));
    await expect(api.post('/x', {})).rejects.toBeInstanceOf(ApiError);
    vi.stubGlobal('fetch', vi.fn(async () => res(422, { detail: [{ field: 'name', message: 'Required' }] })));
    try {
      await api.post('/x', {});
      throw new Error('should have thrown');
    } catch (e) {
      const err = e as ApiError;
      expect(err.status).toBe(422);
      expect(err.fieldError('name')).toBe('Required');
    }
  });

  it("maps FastAPI's default loc/msg validation shape", async () => {
    vi.stubGlobal('fetch', vi.fn(async () => res(422, { detail: [{ loc: ['body', 'last4'], msg: 'bad digits' }] })));
    try {
      await api.post('/x', {});
      throw new Error('should have thrown');
    } catch (e) {
      expect((e as ApiError).fieldError('last4')).toBe('bad digits');
    }
  });

  it('maps a string detail to the error message', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => res(404, { detail: 'not found' })));
    await expect(api.get('/x')).rejects.toMatchObject({ status: 404, message: 'not found' });
  });

  it('preserves structured import lifecycle metadata', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => res(500, {
      detail: 'Commit failed', code: 'commit_failed', import_id: 8, status: 'failed',
    })));
    await expect(api.post('/imports/8/commit', {})).rejects.toMatchObject({
      status: 500, message: 'Commit failed', code: 'commit_failed', importId: 8, lifecycleStatus: 'failed',
    });
  });

  it('surfaces a network failure as an offline ApiError (status 0)', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => {
      throw new TypeError('Failed to fetch');
    }));
    await expect(api.get('/x')).rejects.toMatchObject({ status: 0 });
  });
});

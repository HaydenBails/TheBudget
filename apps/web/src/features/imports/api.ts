import { api, ApiError } from '../../api/client';
import type { ImportCommitResult, ImportDetail, ImportPreview } from './types';

const base = (profileId: number) => `/profiles/${profileId}/imports`;

export async function previewStatement(profileId: number, accountId: number, file: File): Promise<ImportPreview> {
  const body = new FormData();
  body.append('statement', file, file.name);
  body.append('account_id', String(accountId));
  try {
    return await api.postForm<ImportPreview>(`${base(profileId)}/preview`, body);
  } catch (error) {
    if (error instanceof ApiError && error.status === 409 && error.importId != null && error.code?.startsWith('blocked_')) {
      const detail = await api.get<ImportDetail>(`${base(profileId)}/${error.importId}`);
      return { ...detail, suggested_account_id: null };
    }
    throw error;
  }
}

export function commitStatement(profileId: number, importId: number, acknowledgeNeedsReview: boolean) {
  return api.post<ImportCommitResult>(`${base(profileId)}/${importId}/commit`, {
    acknowledge_needs_review: acknowledgeNeedsReview,
  });
}

export function cancelStatement(profileId: number, importId: number) {
  return api.post<{ import_id: number; status: 'cancelled' }>(`${base(profileId)}/${importId}/cancel`);
}

import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api } from '../../api/client';
import { commitStatement, previewStatement } from './api';
import type { ImportDetail, ImportPreview } from './types';

const preview: ImportPreview = {
  id: 9, profile_id: 2, account_id: 4, issuer: 'TD', source_filename: 'statement.pdf',
  parser_name: 'td_credit_card', parser_version: '1', statement_start_date: '2026-01-01',
  statement_end_date: '2026-01-31', currency: 'CAD', status: 'ready', validation_status: 'validated',
  duplicate_decision: 'new', duplicate_of_import_id: null, transaction_count: 0, purchase_count: 0,
  credit_count: 0, payment_count: 0, fee_interest_count: 0, unresolved_count: 0,
  expected_total_cents: 0, parsed_total_cents: 0, reconciliation_delta_cents: 0,
  purchase_total_cents: 0, credit_total_cents: 0, payment_total_cents: 0,
  fee_interest_total_cents: 0, staged_transactions: [], warnings: [], suggested_account_id: 4,
};

afterEach(() => vi.restoreAllMocks());

describe('statement import API', () => {
  it('uploads only the statement and account id as multipart form data', async () => {
    const post = vi.spyOn(api, 'postForm').mockResolvedValue(preview);
    const file = new File(['pdf'], 'statement.pdf', { type: 'application/pdf' });

    await previewStatement(2, 4, file);

    expect(post).toHaveBeenCalledWith('/profiles/2/imports/preview', expect.any(FormData));
    const form = post.mock.calls[0][1];
    expect([...form.keys()]).toEqual(['statement', 'account_id']);
    expect(form.get('statement')).toBeInstanceOf(File);
    expect(form.get('account_id')).toBe('4');
  });

  it('recovers a persisted blocked duplicate for a cancellable preview', async () => {
    vi.spyOn(api, 'postForm').mockRejectedValue(new ApiError('Duplicate statement', 409, [], {
      code: 'blocked_file_hash', importId: 9, duplicateOfImportId: 3, lifecycleStatus: 'staged',
    }));
    const detail: ImportDetail = { ...preview, duplicate_decision: 'blocked_file_hash', duplicate_of_import_id: 3 };
    const get = vi.spyOn(api, 'get').mockResolvedValue(detail);

    await expect(previewStatement(2, 4, new File(['pdf'], 'statement.pdf'))).resolves.toMatchObject({
      id: 9, duplicate_decision: 'blocked_file_hash', suggested_account_id: null,
    });
    expect(get).toHaveBeenCalledWith('/profiles/2/imports/9');
  });

  it('always sends the explicit needs-review acknowledgement', async () => {
    const post = vi.spyOn(api, 'post').mockResolvedValue({});
    await commitStatement(2, 9, false);
    await commitStatement(2, 9, true);
    expect(post).toHaveBeenNthCalledWith(1, '/profiles/2/imports/9/commit', { acknowledge_needs_review: false });
    expect(post).toHaveBeenNthCalledWith(2, '/profiles/2/imports/9/commit', { acknowledge_needs_review: true });
  });
});

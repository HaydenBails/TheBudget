import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../../api/client';
import { ImportPage } from './ImportPage';
import * as importApi from './api';
import type { ImportPreview } from './types';

const profileState = vi.hoisted(() => ({ id: 1 }));

vi.mock('../profiles/ProfileContext', () => ({
  useCurrentProfile: () => ({
    currentProfile: { id: profileState.id, name: 'Personal', base_currency: 'CAD', is_archived: false },
    currentProfileId: profileState.id,
    isLoading: false,
  }),
}));

vi.mock('../accounts/api', () => ({
  useAccounts: () => ({
    data: [{ id: 7, profile_id: 1, issuer: 'TD', display_name: 'Daily Visa', color: '#000', last4: '1234', currency: 'CAD', account_fingerprint: null, is_archived: false, created_at: '', updated_at: '' }],
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
}));

vi.mock('./api', () => ({ previewStatement: vi.fn(), commitStatement: vi.fn(), cancelStatement: vi.fn() }));

const preview: ImportPreview = {
  id: 11, profile_id: 1, account_id: 7, issuer: 'TD', source_filename: 'statement.pdf',
  parser_name: 'td_credit_card', parser_version: '1', statement_start_date: '2026-01-01',
  statement_end_date: '2026-01-31', currency: 'CAD', status: 'ready', validation_status: 'validated',
  duplicate_decision: 'new', duplicate_of_import_id: null, transaction_count: 1, purchase_count: 1,
  credit_count: 0, payment_count: 0, fee_interest_count: 0, unresolved_count: 0,
  expected_total_cents: 1200, parsed_total_cents: 1200, reconciliation_delta_cents: 0,
  purchase_total_cents: 1200, credit_total_cents: 0, payment_total_cents: 0,
  fee_interest_total_cents: 0, warnings: [], suggested_account_id: 7,
  staged_transactions: [{ id: 1, source_row_reference: '1', date: '2026-01-12', posted_date: null,
    raw_description: 'Merchant', merchant: 'Merchant', amount_cents: 1200, currency: 'CAD', direction: 'debit',
    type: 'purchase', included_in_spending: true, exclusion_reason: null, original_foreign_amount_cents: null,
    original_foreign_currency: null, exchange_rate: null, occurrence_index: 1, duplicate_decision: 'new', status: 'pending' }],
};

async function renderAndPreview(user: ReturnType<typeof userEvent.setup>, result: ImportPreview = preview) {
  vi.mocked(importApi.previewStatement).mockResolvedValue(result);
  render(<MemoryRouter><ImportPage /></MemoryRouter>);
  const input = screen.getByLabelText(/Choose or drop a PDF statement/i) as HTMLInputElement;
  await user.upload(input, new File(['pdf'], 'statement.pdf', { type: 'application/pdf' }));
  await user.click(screen.getByRole('button', { name: 'Preview statement' }));
  return screen.findByRole('heading', { name: result.duplicate_decision.startsWith('blocked_') ? 'Duplicate statement blocked' : 'Review before import' });
}

describe('ImportPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    profileState.id = 1;
  });

  it('focuses async results and releases the File after a terminal commit failure', async () => {
    const user = userEvent.setup();
    vi.mocked(importApi.commitStatement).mockRejectedValue(new ApiError('Commit failed', 500, [], {
      code: 'commit_failed', importId: 11, lifecycleStatus: 'failed',
    }));
    const heading = await renderAndPreview(user);
    await waitFor(() => expect(heading).toHaveFocus());
    await user.click(screen.getByRole('button', { name: 'Import 1 transactions' }));

    const alert = await screen.findByRole('alert');
    await waitFor(() => expect(alert).toHaveFocus());
    expect(screen.queryByText('statement.pdf')).not.toBeInTheDocument();
    expect(screen.getByText('Choose or drop a PDF statement')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancel import' })).not.toBeInTheDocument();
  });

  it.each([
    [413, 'Choose a smaller PDF'],
    [415, 'Choose a text-based PDF statement'],
    [422, 'Check the statement and selected account'],
  ])('shows actionable guidance and focuses a preview error for HTTP %s', async (status, guidance) => {
    const user = userEvent.setup();
    vi.mocked(importApi.previewStatement).mockRejectedValue(new ApiError('Preview rejected.', status));
    render(<MemoryRouter><ImportPage /></MemoryRouter>);
    await user.upload(screen.getByLabelText(/Choose or drop a PDF statement/i), new File(['pdf'], 'statement.pdf', { type: 'application/pdf' }));
    await user.click(screen.getByRole('button', { name: 'Preview statement' }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(guidance);
    await waitFor(() => expect(alert).toHaveFocus());
  });

  it('clears the transient File after cancellation', async () => {
    const user = userEvent.setup();
    vi.mocked(importApi.cancelStatement).mockResolvedValue({ import_id: 11, status: 'cancelled' });
    await renderAndPreview(user);
    await user.click(screen.getByRole('button', { name: 'Cancel import' }));
    await waitFor(() => expect(importApi.cancelStatement).toHaveBeenCalledWith(1, 11));
    expect(screen.queryByText('statement.pdf')).not.toBeInTheDocument();
    expect(screen.getByText('Choose or drop a PDF statement')).toBeInTheDocument();
  });

  it('clears the File, focuses success, and links to Transactions after commit', async () => {
    const user = userEvent.setup();
    vi.mocked(importApi.commitStatement).mockResolvedValue({ import_id: 11, status: 'committed', created_count: 1, linked_duplicate_count: 0, transaction_ids: [99] });
    await renderAndPreview(user);
    await user.click(screen.getByRole('button', { name: 'Import 1 transactions' }));
    const success = await screen.findByRole('heading', { name: 'Transactions added' });
    await waitFor(() => expect(success).toHaveFocus());
    expect(importApi.commitStatement).toHaveBeenCalledWith(1, 11, false);
    expect(screen.getByRole('link', { name: 'View transactions' })).toHaveAttribute('href', '/app/transactions');
    expect(screen.queryByText('statement.pdf')).not.toBeInTheDocument();
  });

  it('requires and sends explicit acknowledgement for needs-review previews', async () => {
    const user = userEvent.setup();
    const needsReview: ImportPreview = { ...preview, validation_status: 'needs_review', warnings: [{ id: 3, code: 'reconciliation', severity: 'warning', message: 'Totals need review.', source_row_reference: null }] };
    vi.mocked(importApi.commitStatement).mockResolvedValue({ import_id: 11, status: 'committed', created_count: 1, linked_duplicate_count: 0, transaction_ids: [99] });
    await renderAndPreview(user, needsReview);
    const commit = screen.getByRole('button', { name: 'Import 1 transactions' });
    expect(commit).toBeDisabled();
    await user.click(screen.getByRole('checkbox', { name: /I reviewed the warnings/ }));
    expect(commit).toBeEnabled();
    await user.click(commit);
    await screen.findByRole('heading', { name: 'Transactions added' });
    expect(importApi.commitStatement).toHaveBeenCalledWith(1, 11, true);
  });

  it('releases the native input File on Remove and permits selecting the same file again', async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><ImportPage /></MemoryRouter>);
    const input = screen.getByLabelText(/Choose or drop a PDF statement/i) as HTMLInputElement;
    const file = new File(['pdf'], 'statement.pdf', { type: 'application/pdf' });
    await user.upload(input, file);
    expect(input.files).toHaveLength(1);
    await user.click(screen.getByRole('button', { name: 'Remove selected file' }));
    expect(input.files).toHaveLength(0);
    await user.upload(input, file);
    expect(input.files).toHaveLength(1);
    expect(screen.getByText('statement.pdf')).toBeInTheDocument();
  });

  it('releases the native input File when the current profile changes', async () => {
    const user = userEvent.setup();
    const view = render(<MemoryRouter><ImportPage /></MemoryRouter>);
    const input = screen.getByLabelText(/Choose or drop a PDF statement/i) as HTMLInputElement;
    await user.upload(input, new File(['pdf'], 'statement.pdf', { type: 'application/pdf' }));
    expect(input.files).toHaveLength(1);
    profileState.id = 2;
    view.rerender(<MemoryRouter><ImportPage /></MemoryRouter>);
    await waitFor(() => expect(input.files).toHaveLength(0));
    expect(screen.getByText('Choose or drop a PDF statement')).toBeInTheDocument();
  });
});

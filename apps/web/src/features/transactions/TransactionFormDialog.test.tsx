import { useState } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { TransactionFormDialog } from './TransactionFormDialog';
import type { Account } from '../accounts/types';
import type { Transaction } from './types';

const account: Account = {
  id: 1, profile_id: 1, issuer: 'TD', display_name: 'Daily card', color: '#0ea5e9', last4: '1234', currency: 'CAD', account_fingerprint: null, is_archived: false, created_at: '', updated_at: '',
};

const transaction: Transaction = {
  id: 8, profile_id: 1, account_id: 1, category_id: null, date: '2026-07-15', posted_date: null, raw_description: 'Coffee', merchant: 'Cafe', amount_cents: 425, currency: 'CAD', direction: 'debit', type: 'purchase', categorization_status: 'uncategorized', included_in_spending: true, exclusion_reason: null, recurring_series_id: null, notes: null, source: 'manual', import_id: null, deleted_at: null, created_at: '', updated_at: '',
};

function Harness({ onCreate }: { onCreate: ReturnType<typeof vi.fn> }) {
  const [open, setOpen] = useState(false);
  return <><button type="button" onClick={() => setOpen(true)}>Open form</button>{open && <TransactionFormDialog accounts={[account]} categories={[]} onClose={() => setOpen(false)} onCreate={onCreate} onUpdate={vi.fn()} />}</>;
}

describe('TransactionFormDialog', () => {
  it('rejects a negative debit at the exact-cent boundary', async () => {
    const onCreate = vi.fn();
    const user = userEvent.setup();
    render(<Harness onCreate={onCreate} />);
    await user.click(screen.getByRole('button', { name: 'Open form' }));
    await user.type(screen.getByLabelText('Statement description'), 'Coffee');
    await user.type(screen.getByLabelText(/Amount \(CAD\)/), '-4.25');
    await user.click(screen.getByRole('button', { name: 'Add transaction' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Debit amounts must be positive');
    expect(onCreate).not.toHaveBeenCalled();
  });

  it('traps focus and restores it to the opener after close', async () => {
    const user = userEvent.setup();
    render(<Harness onCreate={vi.fn()} />);
    const opener = screen.getByRole('button', { name: 'Open form' });
    await user.click(opener);
    expect(screen.getByLabelText('Account')).toHaveFocus();
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(opener).toHaveFocus());
  });

  it('focuses the first enabled field when edit mode disables Account', () => {
    render(<TransactionFormDialog accounts={[account]} categories={[]} initial={transaction} onClose={vi.fn()} onCreate={vi.fn()} onUpdate={vi.fn()} />);
    expect(screen.getByLabelText('Account')).toBeDisabled();
    expect(screen.getByLabelText('Date')).toHaveFocus();
  });
});

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ApiError } from '../../api/client';
import type { Account } from '../accounts/types';
import type { Category } from '../categories/types';
import { centsToInput, parseCadToCents } from './money';
import type { Direction, Transaction, TransactionCreate, TransactionType, TransactionUpdate } from './types';
import { TRANSACTION_TYPES, transactionTypeLabel } from './types';
import { useDialogFocus } from './useDialogFocus';

interface Props {
  accounts: Account[];
  categories: Category[];
  initial?: Transaction | null;
  onClose: () => void;
  onCreate: (body: TransactionCreate) => Promise<unknown>;
  onUpdate: (id: number, body: TransactionUpdate) => Promise<unknown>;
}

export function TransactionFormDialog({ accounts, categories, initial, onClose, onCreate, onUpdate }: Props) {
  const dialogRef = useRef<HTMLElement>(null);
  const [accountId, setAccountId] = useState(String(initial?.account_id ?? accounts[0]?.id ?? ''));
  const [date, setDate] = useState(initial?.date ?? new Date().toISOString().slice(0, 10));
  const [merchant, setMerchant] = useState(initial?.merchant ?? '');
  const [description, setDescription] = useState(initial?.raw_description ?? '');
  const [amount, setAmount] = useState(initial ? centsToInput(initial.amount_cents) : '');
  const [direction, setDirection] = useState<Direction>(initial?.direction ?? 'debit');
  const [type, setType] = useState<TransactionType>(initial?.type ?? 'purchase');
  const [categoryId, setCategoryId] = useState(initial?.category_id ? String(initial.category_id) : '');
  const [notes, setNotes] = useState(initial?.notes ?? '');
  const [included, setIncluded] = useState(initial?.included_in_spending ?? true);
  const [exclusionReason, setExclusionReason] = useState(initial?.exclusion_reason ?? '');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const canInclude = type === 'purchase' || type === 'cash_advance' || type === 'refund';

  useDialogFocus(dialogRef, onClose);

  useEffect(() => {
    if (canInclude) return;
    setIncluded(false);
    setExclusionReason((current) => current || `${TRANSACTION_TYPES.find((item) => item.value === type)?.label ?? 'This type'} is excluded from spending.`);
  }, [canInclude, type]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const cents = parseCadToCents(amount);
    if (!accountId) return setError('Choose an account.');
    if (!date) return setError('Choose a transaction date.');
    if (!description.trim()) return setError('Enter the statement description.');
    if (cents == null) return setError('Enter a non-zero amount with no more than two decimal places.');
    if (direction === 'debit' && cents < 0) return setError('Debit amounts must be positive. Remove the minus sign or choose Credit.');
    if (direction === 'credit' && cents > 0) return setError('Credit amounts must be negative. Add a minus sign or choose Debit.');
    if (initial && !included && !exclusionReason.trim()) return setError('Give a reason when excluding a transaction from spending.');

    setSaving(true);
    try {
      const common = {
        date,
        raw_description: description.trim(),
        merchant: merchant.trim(),
        amount_cents: cents,
        direction,
        type,
        category_id: categoryId ? Number(categoryId) : null,
        notes: notes.trim() || null,
      };
      if (initial) {
        await onUpdate(initial.id, {
          ...common,
          categorization_status: categoryId ? 'manual' : 'uncategorized',
          included_in_spending: included,
          exclusion_reason: included ? null : exclusionReason.trim(),
        });
      } else {
        await onCreate({ ...common, account_id: Number(accountId), currency: 'CAD', source: 'manual' });
      }
      onClose();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'The transaction could not be saved. Try again.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="tx-modal" role="presentation">
      <section ref={dialogRef} className="tx-dialog" role="dialog" aria-modal="true" aria-labelledby="tx-form-title">
        <header className="tx-dialog-head">
          <div><h2 id="tx-form-title">{initial ? 'Edit transaction' : 'Add transaction'}</h2><p>Amounts are stored as exact integer cents.</p></div>
          <button type="button" className="app-btn" onClick={onClose}>Close</button>
        </header>
        <form className="tx-form" onSubmit={submit}>
          {error && <div className="tx-alert" role="alert">{error}</div>}
          <div className="tx-form-grid">
            <label>Account<select data-autofocus={initial ? undefined : true} value={accountId} onChange={(event) => setAccountId(event.target.value)} disabled={Boolean(initial)} required><option value="">Choose an account</option>{accounts.map((account) => <option key={account.id} value={account.id}>{account.display_name}</option>)}</select></label>
            <label>Date<input data-autofocus={initial ? true : undefined} type="date" value={date} onChange={(event) => setDate(event.target.value)} required /></label>
            <label>Merchant<input value={merchant} onChange={(event) => setMerchant(event.target.value)} maxLength={200} /></label>
            <label>Amount (CAD)<input inputMode="decimal" value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="42.50" aria-describedby="tx-amount-help" required /><small id="tx-amount-help">Use a minus sign for credits, for example -25.00.</small></label>
            <label>Direction<select value={direction} onChange={(event) => setDirection(event.target.value as Direction)}><option value="debit">Debit</option><option value="credit">Credit</option></select></label>
            <label>Type<select value={type} onChange={(event) => setType(event.target.value as TransactionType)}>{TRANSACTION_TYPES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
            <label>Category<select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}><option value="">Uncategorized</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
            <label className="tx-span-2">Statement description<input value={description} onChange={(event) => setDescription(event.target.value)} maxLength={500} required /></label>
            <label className="tx-span-2">Notes<textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} /></label>
          </div>
          {initial && <fieldset className="tx-inclusion"><legend>Spending treatment</legend><label className="tx-check"><input type="checkbox" checked={included} onChange={(event) => setIncluded(event.target.checked)} disabled={!canInclude} /> Include in spending totals</label>{!canInclude && <p className="tx-muted">{transactionTypeLabel(type)} transactions are excluded by the Meridian accounting policy.</p>}{!included && <label>Exclusion reason<input value={exclusionReason} onChange={(event) => setExclusionReason(event.target.value)} maxLength={200} required /></label>}</fieldset>}
          <footer className="tx-dialog-actions"><button type="button" className="app-btn" onClick={onClose}>Cancel</button><button type="submit" className="app-btn primary" disabled={saving}>{saving ? 'Saving...' : initial ? 'Save changes' : 'Add transaction'}</button></footer>
        </form>
      </section>
    </div>
  );
}

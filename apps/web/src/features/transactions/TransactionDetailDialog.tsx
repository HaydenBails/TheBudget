import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ApiError } from '../../api/client';
import type { Category } from '../categories/types';
import { useReplaceTransactionSplits, useReplaceTransactionTags, useTransactionDetail } from './api';
import { centsToInput, formatCad, parseCadToCents } from './money';
import type { Transaction } from './types';
import { useDialogFocus } from './useDialogFocus';

interface SplitDraft { categoryId: string; amount: string }

interface Props {
  profileId: number;
  transaction: Transaction;
  categories: Category[];
  onClose: () => void;
  onEdit: (transaction: Transaction) => void;
}

export function TransactionDetailDialog({ profileId, transaction, categories, onClose, onEdit }: Props) {
  const detail = useTransactionDetail(profileId, transaction.id);
  const replaceSplits = useReplaceTransactionSplits(profileId);
  const replaceTags = useReplaceTransactionTags(profileId);
  const dialogRef = useRef<HTMLElement>(null);
  const [splits, setSplits] = useState<SplitDraft[]>([]);
  const [tags, setTags] = useState('');
  const [splitError, setSplitError] = useState<string | null>(null);
  const [tagError, setTagError] = useState<string | null>(null);

  useDialogFocus(dialogRef, onClose);

  useEffect(() => {
    if (!detail.data) return;
    setSplits(detail.data.splits.map((split) => ({ categoryId: String(split.category_id), amount: centsToInput(split.amount_cents) })));
    setTags(detail.data.tags.map((tag) => tag.name).join(', '));
  }, [detail.data]);

  async function saveSplits(event: FormEvent) {
    event.preventDefault();
    setSplitError(null);
    if (splits.length === 1) return setSplitError('Use at least two allocations, or clear the split.');
    const parsed = splits.map((split) => ({ category_id: Number(split.categoryId), amount_cents: parseCadToCents(split.amount) }));
    if (parsed.some((split) => !split.category_id || split.amount_cents == null)) return setSplitError('Choose a category and enter a valid non-zero amount for every allocation.');
    const total = parsed.reduce((sum, split) => sum + (split.amount_cents ?? 0), 0);
    if (parsed.length > 0 && total !== transaction.amount_cents) return setSplitError(`Split total ${formatCad(total)} must equal ${formatCad(transaction.amount_cents)}.`);
    try {
      await replaceSplits.mutateAsync({ id: transaction.id, splits: parsed as Array<{ category_id: number; amount_cents: number }> });
      await detail.refetch();
    } catch (cause) {
      setSplitError(cause instanceof ApiError ? cause.message : 'Could not save the split.');
    }
  }

  async function saveTags(event: FormEvent) {
    event.preventDefault();
    setTagError(null);
    const names = tags.split(',').map((tag) => tag.trim()).filter(Boolean);
    if (names.some((tag) => tag.length > 60)) return setTagError('Each tag must be 60 characters or fewer.');
    try {
      await replaceTags.mutateAsync({ id: transaction.id, tags: names });
      await detail.refetch();
    } catch (cause) {
      setTagError(cause instanceof ApiError ? cause.message : 'Could not save the tags.');
    }
  }

  const current = detail.data ?? transaction;
  return (
    <div className="tx-modal" role="presentation">
      <section ref={dialogRef} className="tx-dialog tx-detail" role="dialog" aria-modal="true" aria-labelledby="tx-detail-title">
        <header className="tx-dialog-head">
          <div><p className="tx-eyebrow">Transaction detail</p><h2 id="tx-detail-title">{current.merchant || current.raw_description}</h2><p>{current.date} · {formatCad(current.amount_cents)} CAD</p></div>
          <button data-autofocus type="button" className="app-btn" onClick={onClose}>Close</button>
        </header>
        {detail.isLoading ? <div className="tx-loading" role="status">Loading transaction detail…</div> : detail.isError ? <div className="tx-alert" role="alert">Could not load transaction detail. <button type="button" onClick={() => detail.refetch()}>Try again</button></div> : <>
          <dl className="tx-detail-grid">
            <div><dt>Description</dt><dd>{current.raw_description}</dd></div><div><dt>Type</dt><dd>{current.type.replace('_', ' ')}</dd></div>
            <div><dt>Spending</dt><dd>{current.included_in_spending ? 'Included' : `Excluded${current.exclusion_reason ? ` — ${current.exclusion_reason}` : ''}`}</dd></div><div><dt>Source</dt><dd>{current.source.replace('_', ' ')}</dd></div>
          </dl>
          <div className="tx-detail-actions"><button type="button" className="app-btn" onClick={() => onEdit(current)}>Edit transaction</button></div>
          <form className="tx-detail-section" onSubmit={saveSplits}>
            <div className="tx-section-head"><div><h3>Category split</h3><p>Use two or more allocations that exactly total {formatCad(transaction.amount_cents)}.</p></div><button type="button" className="app-btn" onClick={() => setSplits((rows) => [...rows, { categoryId: '', amount: '' }])}>Add allocation</button></div>
            {splitError && <div className="tx-alert" role="alert">{splitError}</div>}
            {splits.length === 0 ? <p className="tx-muted">No split — this transaction uses its single category.</p> : <div className="tx-split-list">{splits.map((split, index) => <div className="tx-split-row" key={index}><label>Category<select value={split.categoryId} onChange={(event) => setSplits((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, categoryId: event.target.value } : row))}><option value="">Choose</option>{categories.map((category) => <option value={category.id} key={category.id}>{category.name}</option>)}</select></label><label>Amount (CAD)<input inputMode="decimal" value={split.amount} onChange={(event) => setSplits((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, amount: event.target.value } : row))} /></label><button type="button" className="tx-remove" onClick={() => setSplits((rows) => rows.filter((_, rowIndex) => rowIndex !== index))}>Remove</button></div>)}</div>}
            <div className="tx-dialog-actions"><button type="button" className="app-btn" onClick={() => setSplits([])}>Clear split</button><button type="submit" className="app-btn primary" disabled={replaceSplits.isPending}>{replaceSplits.isPending ? 'Saving...' : 'Save split'}</button></div>
          </form>
          <form className="tx-detail-section" onSubmit={saveTags}>
            <h3>Tags</h3><label>Comma-separated tags<input value={tags} onChange={(event) => setTags(event.target.value)} placeholder="recurring, work" /></label><p className="tx-muted">Tag names are reused within this profile and matched without regard to case.</p>
            {tagError && <div className="tx-alert" role="alert">{tagError}</div>}
            <div className="tx-dialog-actions"><button type="submit" className="app-btn primary" disabled={replaceTags.isPending}>{replaceTags.isPending ? 'Saving...' : 'Save tags'}</button></div>
          </form>
        </>}
      </section>
    </div>
  );
}

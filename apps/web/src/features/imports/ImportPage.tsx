import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError } from '../../api/client';
import { useAccounts } from '../accounts/api';
import { useCurrentProfile } from '../profiles/ProfileContext';
import { formatCad } from '../transactions/money';
import { cancelStatement, commitStatement, previewStatement } from './api';
import type { ImportCommitResult, ImportPreview } from './types';
import './imports.css';

type BusyAction = 'preview' | 'commit' | 'cancel' | null;

const XLSX_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
const CSV_TYPES = new Set(['text/csv', 'application/csv', 'application/vnd.ms-excel', 'application/octet-stream', 'text/plain']);

function isSupportedStatement(file: File) {
  const name = file.name.toLowerCase();
  if (name.endsWith('.pdf')) return !file.type || file.type === 'application/pdf';
  if (name.endsWith('.xlsx')) return !file.type || file.type === XLSX_TYPE || file.type === 'application/octet-stream';
  if (name.endsWith('.csv')) return !file.type || CSV_TYPES.has(file.type);
  return false;
}

function amount(value: number | null) {
  return value == null ? 'Not provided' : formatCad(value);
}

function errorMessage(error: unknown) {
  if (!(error instanceof ApiError)) return 'Something went wrong. Try again.';
  const guidance: Record<number, string> = {
    0: 'Start the local API, then try again.',
    409: 'Review the current import state before continuing.',
    413: 'Choose a smaller PDF and try again.',
    415: 'Choose a text-based PDF statement.',
    422: 'Check the statement and selected account, then try again.',
    500: 'Nothing was imported. Choose the statement again when you are ready to retry.',
  };
  return `${error.message} ${guidance[error.status] ?? 'Try again.'}`;
}

export function ImportPage() {
  const profile = useCurrentProfile();
  const profileId = profile.currentProfileId;
  const accountsQuery = useAccounts(profileId, false);
  const accounts = accountsQuery.data ?? [];
  const [file, setFile] = useState<File | null>(null);
  const [accountId, setAccountId] = useState<number | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [success, setSuccess] = useState<ImportCommitResult | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [busy, setBusy] = useState<BusyAction>(null);
  const [error, setError] = useState('');
  const [dragging, setDragging] = useState(false);
  const resultHeading = useRef<HTMLHeadingElement>(null);
  const errorBox = useRef<HTMLDivElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setFile(null);
    setPreview(null);
    setSuccess(null);
    setAcknowledged(false);
    setError('');
    setAccountId(null);
    if (fileInput.current) fileInput.current.value = '';
  }, [profileId]);

  useEffect(() => {
    if (accountId == null && accounts.length > 0) setAccountId(accounts[0].id);
  }, [accounts, accountId]);

  useEffect(() => {
    if (error) errorBox.current?.focus();
  }, [error]);

  useEffect(() => {
    if (preview || success) resultHeading.current?.focus();
  }, [preview, success]);

  function chooseFile(next: File | null) {
    setError('');
    setPreview(null);
    setSuccess(null);
    setAcknowledged(false);
    if (next == null && fileInput.current) fileInput.current.value = '';
    if (next && !isSupportedStatement(next)) {
      setFile(null);
      if (fileInput.current) fileInput.current.value = '';
      setError('Choose one PDF, Amex Excel (.xlsx), or TD CSV (.csv) statement. Scans and image files are not supported.');
      return;
    }
    setFile(next);
  }

  async function createPreview() {
    if (profileId == null || accountId == null || file == null) return;
    setBusy('preview');
    setError('');
    try {
      const result = await previewStatement(profileId, accountId, file);
      setPreview(result);
      setAcknowledged(false);
    } catch (nextError) {
      setError(errorMessage(nextError));
    } finally {
      setBusy(null);
    }
  }

  async function cancelPreview() {
    if (profileId == null || preview == null) return;
    setBusy('cancel');
    setError('');
    try {
      await cancelStatement(profileId, preview.id);
      setFile(null);
      setPreview(null);
      setAcknowledged(false);
    } catch (nextError) {
      setError(errorMessage(nextError));
    } finally {
      setBusy(null);
    }
  }

  async function commitPreview() {
    if (profileId == null || preview == null) return;
    setBusy('commit');
    setError('');
    try {
      const result = await commitStatement(profileId, preview.id, acknowledged);
      setSuccess(result);
      setFile(null);
      setPreview(null);
      setAcknowledged(false);
    } catch (nextError) {
      if (nextError instanceof ApiError && nextError.lifecycleStatus === 'failed') {
        setFile(null);
        setPreview(null);
        setAcknowledged(false);
      }
      setError(errorMessage(nextError));
    } finally {
      setBusy(null);
    }
  }

  if (profile.isLoading) return <section className="im-state" role="status">Loading your Meridian profile…</section>;
  if (!profile.currentProfile || profileId == null) return <section className="im-state"><h1>Import statement</h1><div className="app-card app-placeholder"><h2>Choose a profile first</h2><p>Imports are isolated to one profile and one account.</p><div className="app-placeholder-actions"><Link className="app-btn primary" to="/app/profiles">Manage profiles</Link></div></div></section>;

  if (success) {
    return <section className="im-page" aria-labelledby="im-success-title">
      <div className="app-head"><div><p className="im-eyebrow">Import complete</p><h1 id="im-success-title" ref={resultHeading} tabIndex={-1}>Transactions added</h1><p>The statement file has been released from browser memory.</p></div></div>
      <div className="app-card im-success" role="status">
        <div className="im-success-mark" aria-hidden="true">✓</div>
        <div><strong>{success.created_count} created</strong><p>{success.linked_duplicate_count} exact duplicate{success.linked_duplicate_count === 1 ? '' : 's'} linked without creating another transaction.</p></div>
      </div>
      <div className="im-actions"><Link className="app-btn primary" to="/app/transactions">View transactions</Link><button className="app-btn" type="button" onClick={() => setSuccess(null)}>Import another statement</button></div>
    </section>;
  }

  const blocked = preview?.duplicate_decision === 'blocked_file_hash' || preview?.duplicate_decision === 'blocked_logical_key';
  const needsReview = preview?.validation_status === 'needs_review';
  const skipped = preview?.staged_transactions.filter((row) => row.status === 'skipped' || row.duplicate_decision === 'skip_exact').length ?? 0;
  const suggested = accounts.find((item) => item.id === preview?.suggested_account_id);

  return <section className="im-page" aria-labelledby="im-title">
    <div className="app-head"><div><p className="im-eyebrow">Local statement import</p><h1 id="im-title">Import statement</h1><p>{profile.currentProfile.name} · TD/Amex PDF, Amex Excel (.xlsx), or TD CSV (.csv) · one file at a time</p></div></div>

    {error && <div className="im-alert" role="alert" tabIndex={-1} ref={errorBox}><strong>Import needs attention</strong><span>{error}</span></div>}

    {!preview && <div className="im-layout">
      <div className="app-card im-upload-card">
        <div className="im-step"><span>1</span><div><h2>Select a statement</h2><p>The file stays in temporary browser memory and is never saved by Meridian.</p></div></div>
        <label className={`im-drop ${dragging ? 'dragging' : ''}`} onDragEnter={(event) => { event.preventDefault(); setDragging(true); }} onDragOver={(event) => event.preventDefault()} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files[0] ?? null); }}>
          <input ref={fileInput} type="file" accept="application/pdf,.pdf,.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,.csv,text/csv" onChange={(event) => chooseFile(event.target.files?.[0] ?? null)} />
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4m0 0L7 9m5-5 5 5M5 14v5h14v-5" /></svg>
          <strong>{file ? file.name : 'Choose or drop a statement'}</strong>
          <span>{file ? `${Math.max(1, Math.ceil(file.size / 1024)).toLocaleString()} KB selected` : 'Text-based PDF, Amex Excel (.xlsx), or TD CSV (.csv) · one file per import'}</span>
        </label>
        {file && <button className="im-text-button" type="button" onClick={() => chooseFile(null)}>Remove selected file</button>}
      </div>

      <div className="app-card im-account-card">
        <div className="im-step"><span>2</span><div><h2>Choose the account</h2><p>Selection is explicit; Meridian will show its issuer-based suggestion after preview.</p></div></div>
        {accountsQuery.isLoading ? <p role="status">Loading accounts…</p> : accountsQuery.isError ? <div className="im-inline-error" role="alert">Accounts could not be loaded. <button type="button" onClick={() => accountsQuery.refetch()}>Try again</button></div> : accounts.length === 0 ? <div className="im-empty"><p>Create an active account before importing.</p><Link className="app-btn" to="/app/accounts">Manage accounts</Link></div> : <label className="im-field">Account<select value={accountId ?? ''} onChange={(event) => setAccountId(Number(event.target.value))}>{accounts.map((item) => <option key={item.id} value={item.id}>{item.display_name} · {item.issuer}{item.last4 ? ` •••• ${item.last4}` : ''}</option>)}</select></label>}
        <button className="app-btn primary im-preview-button" type="button" disabled={!file || accountId == null || busy != null} onClick={createPreview}>{busy === 'preview' ? 'Reading statement…' : 'Preview statement'}</button>
        <p className="im-privacy">Raw file bytes and full extracted content are never stored in the database.</p>
      </div>
    </div>}

    {preview && <div className="im-preview">
      <div className="app-card im-preview-head">
        <div><p className="im-eyebrow">Preview ready</p><h2 ref={resultHeading} tabIndex={-1}>{blocked ? 'Duplicate statement blocked' : 'Review before import'}</h2><p>{preview.source_filename} · {preview.issuer} · {preview.statement_start_date ?? 'Unknown start'} to {preview.statement_end_date ?? 'Unknown end'}</p></div>
        <span className={`im-status ${blocked || needsReview ? 'review' : 'ready'}`}>{blocked ? 'Duplicate' : needsReview ? 'Needs review' : 'Validated'}</span>
      </div>

      {suggested && <div className="im-suggestion"><strong>Suggested account:</strong> {suggested.display_name}{suggested.id === preview.account_id ? ' (selected)' : ' (different from selected account)'}</div>}
      {blocked && <div className="im-alert" role="status"><strong>No duplicate transactions will be created.</strong><span>This statement matches import #{preview.duplicate_of_import_id}. Cancel this blocked attempt to clear it.</span></div>}

      <div className="im-counts" aria-label="Statement transaction counts">
        {[['Transactions', preview.transaction_count], ['Purchases', preview.purchase_count], ['Credits', preview.credit_count], ['Payments', preview.payment_count], ['Fees + interest', preview.fee_interest_count], ['Skipped exact', skipped]].map(([label, value]) => <div className="app-card" key={label}><span>{label}</span><strong>{value}</strong></div>)}
      </div>

      <div className="im-review-grid">
        <div className="app-card"><h3>Reconciliation</h3><dl className="im-totals"><div><dt>Expected</dt><dd>{amount(preview.expected_total_cents)}</dd></div><div><dt>Parsed</dt><dd>{amount(preview.parsed_total_cents)}</dd></div><div><dt>Difference</dt><dd>{amount(preview.reconciliation_delta_cents)}</dd></div></dl></div>
        <div className="app-card"><h3>Warnings</h3>{preview.warnings.length === 0 ? <p className="im-muted">No statement warnings.</p> : <ul className="im-warnings">{preview.warnings.map((warning) => <li key={warning.id}><strong>{warning.severity}</strong><span>{warning.message}</span></li>)}</ul>}</div>
      </div>

      {preview.staged_transactions.length > 0 && <div className="app-card im-candidates"><h3>Parsed transactions</h3><div className="im-candidate-list">{preview.staged_transactions.map((row) => <div className="im-candidate" key={row.id}><div><strong>{row.merchant || row.raw_description}</strong><span>{row.date} · {row.type.replace('_', ' ')}</span></div><div><b>{formatCad(row.amount_cents)}</b><span>{row.duplicate_decision === 'potential_overlap' ? 'Possible overlap' : row.status}</span></div></div>)}</div></div>}

      {needsReview && !blocked && <label className="im-ack"><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} /><span><strong>I reviewed the warnings and possible overlaps.</strong> Import these rows with the displayed totals.</span></label>}

      <div className="im-actions"><button className="app-btn" type="button" onClick={cancelPreview} disabled={busy != null}>{busy === 'cancel' ? 'Cancelling…' : 'Cancel import'}</button><button className="app-btn primary" type="button" onClick={commitPreview} disabled={busy != null || blocked || (needsReview && !acknowledged)}>{busy === 'commit' ? 'Importing…' : `Import ${preview.transaction_count - skipped} transactions`}</button></div>
    </div>}
  </section>;
}

import {
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type PaginationState,
  type RowSelectionState,
  type SortingState,
  type Updater,
} from '@tanstack/react-table';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ApiError } from '../../api/client';
import { useAccounts } from '../accounts/api';
import type { Account } from '../accounts/types';
import { useCategories } from '../categories/api';
import type { Category } from '../categories/types';
import { CategoryIcon } from '../categories/CategoryIcon';
import { useCurrentProfile } from '../profiles/ProfileContext';
import {
  useBulkUpdateTransactions,
  useCreateTransaction,
  useDeleteTransaction,
  useRestoreTransaction,
  useTransactions,
  useUpdateTransaction,
} from './api';
import { formatCad } from './money';
import { buildBulkAction, canBulkInclude, type BulkActionChoice } from './bulk';
import { TransactionDetailDialog } from './TransactionDetailDialog';
import { TransactionFormDialog } from './TransactionFormDialog';
import type { Transaction, TransactionFilters, TransactionType } from './types';
import { TRANSACTION_TYPES, transactionTypeLabel } from './types';
import { useDialogFocus } from './useDialogFocus';
import './transactions.css';

const INITIAL_FILTERS: TransactionFilters = {
  accountId: null,
  categoryId: null,
  type: null,
  dateFrom: '',
  dateTo: '',
  includedInSpending: null,
  search: '',
  includeDeleted: false,
};

const SORTABLE_COLUMNS = new Set(['date', 'merchant', 'account', 'category', 'type', 'spending', 'amount_cents']);
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

function positiveId(value: string | null): number | null {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function safeDate(value: string | null): string {
  return value && ISO_DATE.test(value) ? value : '';
}

function filtersFromParams(params: URLSearchParams): TransactionFilters {
  const included = params.get('included');
  const type = params.get('type');
  return {
    accountId: positiveId(params.get('account')),
    categoryId: positiveId(params.get('category')),
    type: TRANSACTION_TYPES.some((item) => item.value === type) ? type as TransactionType : null,
    dateFrom: safeDate(params.get('from')),
    dateTo: safeDate(params.get('to')),
    includedInSpending: included === 'true' ? true : included === 'false' ? false : null,
    search: params.get('q') ?? '',
    includeDeleted: params.get('trash') === 'true',
  };
}

function sortingFromParams(params: URLSearchParams): SortingState {
  const id = params.get('sort') ?? 'date';
  return [{ id: SORTABLE_COLUMNS.has(id) ? id : 'date', desc: params.get('dir') !== 'asc' }];
}

function paginationFromParams(params: URLSearchParams): PaginationState {
  const page = Number(params.get('page'));
  const size = Number(params.get('size'));
  return { pageIndex: Number.isInteger(page) && page > 0 ? page - 1 : 0, pageSize: [10, 20, 50].includes(size) ? size : 20 };
}

function stateToParams(filters: TransactionFilters, sorting: SortingState, pagination: PaginationState): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.search) params.set('q', filters.search);
  if (filters.accountId != null) params.set('account', String(filters.accountId));
  if (filters.categoryId != null) params.set('category', String(filters.categoryId));
  if (filters.type) params.set('type', filters.type);
  if (filters.dateFrom) params.set('from', filters.dateFrom);
  if (filters.dateTo) params.set('to', filters.dateTo);
  if (filters.includedInSpending != null) params.set('included', String(filters.includedInSpending));
  if (filters.includeDeleted) params.set('trash', 'true');
  const sort = sorting[0];
  if (sort && (sort.id !== 'date' || !sort.desc)) { params.set('sort', sort.id); params.set('dir', sort.desc ? 'desc' : 'asc'); }
  if (pagination.pageIndex > 0) params.set('page', String(pagination.pageIndex + 1));
  if (pagination.pageSize !== 20) params.set('size', String(pagination.pageSize));
  return params;
}

function nameForAccount(accounts: Account[], id: number) {
  return accounts.find((account) => account.id === id)?.display_name ?? `Account ${id}`;
}

function categoryFor(categories: Category[], id: number | null) {
  return id == null ? null : categories.find((category) => category.id === id) ?? null;
}

interface ConfirmDialogProps {
  title: string;
  description: string;
  confirmLabel: string;
  pending: boolean;
  danger?: boolean;
  onCancel: () => void;
  onConfirm: () => void | Promise<void>;
}

function ConfirmDialog({ title, description, confirmLabel, pending, danger = false, onCancel, onConfirm }: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLElement>(null);
  useDialogFocus(dialogRef, onCancel);
  return (
    <div className="tx-modal" role="presentation">
      <section ref={dialogRef} className="tx-confirm" role="alertdialog" aria-modal="true" aria-labelledby="tx-confirm-title">
        <h2 id="tx-confirm-title">{title}</h2>
        <p>{description}</p>
        <div className="tx-dialog-actions">
          <button data-autofocus type="button" className="app-btn" onClick={onCancel}>Cancel</button>
          <button type="button" className={`app-btn ${danger ? 'danger-solid' : 'primary'}`} disabled={pending} onClick={onConfirm}>{pending ? 'Updating...' : confirmLabel}</button>
        </div>
      </section>
    </div>
  );
}

export function TransactionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const profile = useCurrentProfile();
  const profileId = profile.currentProfileId;
  const accountsQuery = useAccounts(profileId);
  const categoriesQuery = useCategories(profileId);
  const accounts = useMemo(() => accountsQuery.data ?? [], [accountsQuery.data]);
  const categories = useMemo(() => categoriesQuery.data ?? [], [categoriesQuery.data]);
  const initialFilters = useMemo(() => filtersFromParams(searchParams), []);
  const [filterDraft, setFilterDraft] = useState(initialFilters);
  const [search, setSearch] = useState(initialFilters.search);
  const [filters, setFilters] = useState(initialFilters);
  const [selection, setSelection] = useState<RowSelectionState>({});
  const [sorting, setSorting] = useState<SortingState>(() => sortingFromParams(searchParams));
  const [pagination, setPagination] = useState<PaginationState>(() => paginationFromParams(searchParams));
  const filtersRef = useRef(filters);
  const sortingRef = useRef(sorting);
  const paginationRef = useRef(pagination);
  filtersRef.current = filters;
  sortingRef.current = sorting;
  paginationRef.current = pagination;
  const [formTransaction, setFormTransaction] = useState<Transaction | 'new' | null>(null);
  const [detailTransaction, setDetailTransaction] = useState<Transaction | null>(null);
  const [deleteTransaction, setDeleteTransaction] = useState<Transaction | null>(null);
  const [bulkAction, setBulkAction] = useState<BulkActionChoice>('categorize');
  const [bulkCategory, setBulkCategory] = useState('');
  const [bulkReason, setBulkReason] = useState('');
  const [confirmBulk, setConfirmBulk] = useState(false);
  const [liveMessage, setLiveMessage] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);
  const previousProfileId = useRef(profileId);
  const normalizedInitialUrl = useRef(false);

  useEffect(() => {
    if (normalizedInitialUrl.current) return;
    normalizedInitialUrl.current = true;
    setSearchParams(stateToParams(filtersRef.current, sortingRef.current, paginationRef.current), { replace: true });
  }, [setSearchParams]);

  useEffect(() => {
    if (search === filtersRef.current.search) return;
    const timer = window.setTimeout(() => {
      const next = { ...filtersRef.current, search };
      const resetPage = { ...paginationRef.current, pageIndex: 0 };
      setFilters(next);
      setPagination(resetPage);
      setSearchParams(stateToParams(next, sortingRef.current, resetPage), { replace: true });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [search, setSearchParams]);

  useEffect(() => {
    if (previousProfileId.current == null || previousProfileId.current === profileId) {
      previousProfileId.current = profileId;
      return;
    }
    previousProfileId.current = profileId;
    setSelection({});
    setDetailTransaction(null);
    setFormTransaction(null);
    setDeleteTransaction(null);
    setConfirmBulk(false);
    setBulkAction('categorize');
    setBulkCategory('');
    setBulkReason('');
    setSearch('');
    setFilterDraft(INITIAL_FILTERS);
    setFilters(INITIAL_FILTERS);
    setSorting([{ id: 'date', desc: true }]);
    setPagination({ pageIndex: 0, pageSize: 20 });
    setSearchParams({}, { replace: true });
    setActionError(null);
  }, [profileId, setSearchParams]);

  const transactionsQuery = useTransactions(profileId, filters);
  const createMutation = useCreateTransaction(profileId ?? 0);
  const updateMutation = useUpdateTransaction(profileId ?? 0);
  const deleteMutation = useDeleteTransaction(profileId ?? 0);
  const restoreMutation = useRestoreTransaction(profileId ?? 0);
  const bulkMutation = useBulkUpdateTransactions(profileId ?? 0);

  async function updateCategory(transaction: Transaction, value: string) {
    setActionError(null);
    try {
      await updateMutation.mutateAsync({ id: transaction.id, body: { category_id: value ? Number(value) : null, categorization_status: value ? 'manual' : 'uncategorized' } });
      setLiveMessage(`Category updated for ${transaction.merchant || transaction.raw_description}.`);
    } catch (cause) {
      const message = cause instanceof ApiError ? cause.message : 'Category update failed.';
      setLiveMessage(message);
      setActionError(`${message} Choose the category again to retry.`);
    }
  }

  async function restore(item: Transaction) {
    setActionError(null);
    try {
      await restoreMutation.mutateAsync(item.id);
      setLiveMessage('Transaction restored.');
    } catch (cause) {
      setActionError(`${cause instanceof ApiError ? cause.message : 'Restore failed.'} Use Restore to try again.`);
    }
  }

  const columns = useMemo<ColumnDef<Transaction>[]>(() => [
    {
      id: 'select',
      enableSorting: false,
      header: ({ table }) => <label className="tx-checkbox-hit"><input type="checkbox" aria-label="Select all transactions on this page" checked={table.getIsAllPageRowsSelected()} ref={(element) => { if (element) element.indeterminate = table.getIsSomePageRowsSelected(); }} onChange={table.getToggleAllPageRowsSelectedHandler()} /></label>,
      cell: ({ row }) => <label className="tx-checkbox-hit"><input type="checkbox" aria-label={`Select ${row.original.merchant || row.original.raw_description}`} checked={row.getIsSelected()} onChange={row.getToggleSelectedHandler()} /></label>,
    },
    { accessorKey: 'date', header: 'Date', cell: ({ getValue }) => <time dateTime={String(getValue())}>{String(getValue())}</time> },
    {
      id: 'merchant',
      accessorFn: (row) => row.merchant || row.raw_description,
      header: 'Merchant / description',
      cell: ({ row }) => <button type="button" className="tx-merchant" onClick={() => setDetailTransaction(row.original)}><strong>{row.original.merchant || row.original.raw_description}</strong>{row.original.merchant && <small>{row.original.raw_description}</small>}</button>,
    },
    { id: 'account', accessorFn: (row) => nameForAccount(accounts, row.account_id), header: 'Account' },
    {
      id: 'category',
      accessorFn: (row) => categoryFor(categories, row.category_id)?.name ?? 'Uncategorized',
      header: 'Category',
      cell: ({ row }) => <label className="tx-inline-category"><span className="tx-sr-only">Category for {row.original.merchant || row.original.raw_description}</span><select value={row.original.category_id ?? ''} onChange={(event) => updateCategory(row.original, event.target.value)} disabled={updateMutation.isPending || Boolean(row.original.deleted_at)}><option value="">Uncategorized</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>,
    },
    { id: 'type', accessorFn: (row) => transactionTypeLabel(row.type), header: 'Type' },
    {
      id: 'spending',
      accessorFn: (row) => row.included_in_spending ? 'Included' : 'Excluded',
      header: 'Spending',
      cell: ({ row }) => <span className={`tx-state ${row.original.included_in_spending ? 'included' : 'excluded'}`}>{row.original.included_in_spending ? 'Included' : 'Excluded'}{!row.original.included_in_spending && row.original.exclusion_reason && <small>{row.original.exclusion_reason}</small>}</span>,
    },
    {
      accessorKey: 'amount_cents',
      header: 'Amount',
      cell: ({ row }) => <span className={`tx-amount ${row.original.amount_cents < 0 ? 'credit' : ''}`}>{formatCad(row.original.amount_cents)}</span>,
    },
    {
      id: 'actions',
      enableSorting: false,
      header: 'Actions',
      cell: ({ row }) => { const name = row.original.merchant || row.original.raw_description; return <div className="tx-row-actions"><button type="button" aria-label={`Edit ${name}`} onClick={() => setFormTransaction(row.original)} disabled={Boolean(row.original.deleted_at)}>Edit</button>{row.original.deleted_at ? <button type="button" aria-label={`Restore ${name}`} onClick={() => restore(row.original)}>Restore</button> : <button type="button" className="danger" aria-label={`Move ${name} to trash`} onClick={() => setDeleteTransaction(row.original)}>Trash</button>}</div>; },
    },
  ], [accounts, categories, restoreMutation, updateMutation]);

  const table = useReactTable({
    data: transactionsQuery.data ?? [],
    columns,
    onRowSelectionChange: setSelection,
    onSortingChange: (updater: Updater<SortingState>) => {
      const next = typeof updater === 'function' ? updater(sortingRef.current) : updater;
      setSorting(next);
      setSearchParams(stateToParams(filters, next, pagination), { replace: true });
    },
    onPaginationChange: (updater: Updater<PaginationState>) => {
      const next = typeof updater === 'function' ? updater(paginationRef.current) : updater;
      setPagination(next);
      setSearchParams(stateToParams(filters, sorting, next), { replace: true });
    },
    getRowId: (row) => String(row.id),
    enableRowSelection: (row) => !row.original.deleted_at,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    state: { rowSelection: selection, sorting, pagination },
  });

  const selectedIds = table.getSelectedRowModel().rows.map((row) => row.original.id);
  const selectedTransactions = table.getSelectedRowModel().rows.map((row) => row.original);
  const selectedCanInclude = canBulkInclude(selectedTransactions);

  function applyFilters() {
    const next = { ...filterDraft, search };
    const nextPage = { ...pagination, pageIndex: 0 };
    setFilters(next);
    setPagination(nextPage);
    setSearchParams(stateToParams(next, sorting, nextPage), { replace: true });
  }

  function resetFilters() {
    setFilterDraft(INITIAL_FILTERS);
    setSearch('');
    setFilters(INITIAL_FILTERS);
    setSorting([{ id: 'date', desc: true }]);
    setPagination({ pageIndex: 0, pageSize: 20 });
    setSearchParams({}, { replace: true });
  }

  async function runBulk() {
    setActionError(null);
    const body = buildBulkAction(bulkAction, selectedIds, bulkCategory, bulkReason);
    try {
      const result = await bulkMutation.mutateAsync(body);
      setLiveMessage(`${result.updated_count} transaction${result.updated_count === 1 ? '' : 's'} updated.`);
      setSelection({});
      setConfirmBulk(false);
    } catch (cause) {
      const message = cause instanceof ApiError ? cause.message : 'Bulk update failed.';
      setLiveMessage(message);
      setActionError(`${message} Review the selected transactions and try again.`);
      setConfirmBulk(false);
    }
  }

  if (profile.isLoading) return <section className="tx-state-page" role="status">Loading your Meridian profile…</section>;
  if (profile.isError) return <section className="tx-state-page"><h1>Transactions</h1><div className="tx-alert" role="alert">Profiles could not be loaded. Restart the local API and try again.</div></section>;
  if (!profile.currentProfile || profileId == null) return <section className="tx-state-page"><h1>Transactions</h1><div className="app-card app-placeholder"><h2>Choose a profile first</h2><p>Transactions are always isolated to one Meridian profile.</p><div className="app-placeholder-actions"><Link className="app-btn primary" to="/app/profiles">Manage profiles</Link></div></div></section>;

  const dataLoading = transactionsQuery.isLoading || accountsQuery.isLoading || categoriesQuery.isLoading;
  const dataError = transactionsQuery.isError || accountsQuery.isError || categoriesQuery.isError;

  return (
    <section className="tx-page" aria-labelledby="tx-page-title">
      <div className="app-head"><div><h1 id="tx-page-title">Transactions</h1><p>{profile.currentProfile.name} · API-backed Meridian workspace</p></div><button type="button" className="app-btn primary" onClick={() => setFormTransaction('new')} disabled={accounts.length === 0}>Add transaction</button></div>
      <div className="tx-live tx-sr-only" aria-live="polite">{liveMessage}</div>
      {actionError && <div className="tx-alert" role="alert"><span>{actionError}</span><button type="button" onClick={() => setActionError(null)}>Dismiss</button></div>}
      {accounts.length === 0 && !accountsQuery.isLoading && <div className="tx-callout"><strong>Add an account before recording transactions.</strong><Link to="/app/accounts">Manage accounts</Link></div>}

      <form className="tx-filters app-card" onSubmit={(event) => { event.preventDefault(); applyFilters(); }}>
        <label className="tx-search">Search transactions<input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Merchant, description, notes, or tag" /></label>
        <label>Account<select value={filterDraft.accountId ?? ''} onChange={(event) => setFilterDraft((current) => ({ ...current, accountId: event.target.value ? Number(event.target.value) : null }))}><option value="">All accounts</option>{accounts.map((account) => <option key={account.id} value={account.id}>{account.display_name}</option>)}</select></label>
        <label>Category<select value={filterDraft.categoryId ?? ''} onChange={(event) => setFilterDraft((current) => ({ ...current, categoryId: event.target.value ? Number(event.target.value) : null }))}><option value="">All categories</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
        <label>Type<select value={filterDraft.type ?? ''} onChange={(event) => setFilterDraft((current) => ({ ...current, type: event.target.value ? event.target.value as TransactionType : null }))}><option value="">All types</option>{TRANSACTION_TYPES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
        <label>Spending<select value={filterDraft.includedInSpending == null ? '' : String(filterDraft.includedInSpending)} onChange={(event) => setFilterDraft((current) => ({ ...current, includedInSpending: event.target.value === '' ? null : event.target.value === 'true' }))}><option value="">Included and excluded</option><option value="true">Included only</option><option value="false">Excluded only</option></select></label>
        <label>From<input type="date" value={filterDraft.dateFrom} onChange={(event) => setFilterDraft((current) => ({ ...current, dateFrom: event.target.value }))} /></label>
        <label>To<input type="date" value={filterDraft.dateTo} onChange={(event) => setFilterDraft((current) => ({ ...current, dateTo: event.target.value }))} /></label>
        <label className="tx-check tx-trash-toggle"><input type="checkbox" checked={filterDraft.includeDeleted} onChange={(event) => setFilterDraft((current) => ({ ...current, includeDeleted: event.target.checked }))} /> Show trash</label>
        <div className="tx-filter-actions"><button className="app-btn primary" type="submit">Apply filters</button><button className="app-btn" type="button" onClick={resetFilters}>Reset</button></div>
      </form>

      {selectedIds.length > 0 && <div className="tx-bulk app-card" aria-label="Bulk transaction actions"><strong>{selectedIds.length} selected</strong><label>Action<select value={bulkAction} onChange={(event) => setBulkAction(event.target.value as BulkActionChoice)}><option value="categorize">Set category</option><option value="include">Include in spending</option><option value="exclude">Exclude from spending</option></select></label>{bulkAction === 'categorize' && <label>Category<select value={bulkCategory} onChange={(event) => setBulkCategory(event.target.value)}><option value="">Uncategorized</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>}{bulkAction === 'exclude' && <label className="tx-bulk-reason">Reason<input value={bulkReason} maxLength={200} onChange={(event) => setBulkReason(event.target.value)} required /></label>}{bulkAction === 'include' && !selectedCanInclude && <p className="tx-bulk-policy" role="alert">Only purchases and cash advances can be included. Remove payments, refunds, transfers, fees, interest, income, adjustments, or unknown items from this selection.</p>}<button type="button" className="app-btn primary" disabled={(bulkAction === 'exclude' && !bulkReason.trim()) || (bulkAction === 'include' && !selectedCanInclude)} onClick={() => setConfirmBulk(true)}>Review update</button><button type="button" className="app-btn" onClick={() => setSelection({})}>Clear</button></div>}

      {dataLoading ? <div className="tx-loading app-card" role="status">Loading profile transactions…</div> : dataError ? <div className="tx-alert app-card" role="alert">Transactions could not be loaded. Check the local API, then <button type="button" onClick={() => { transactionsQuery.refetch(); accountsQuery.refetch(); categoriesQuery.refetch(); }}>try again</button>.</div> : table.getRowModel().rows.length === 0 ? <div className="app-card app-placeholder"><h2>No matching transactions</h2><p>{filters.search || filters.accountId || filters.categoryId || filters.type || filters.dateFrom || filters.dateTo || filters.includedInSpending != null || filters.includeDeleted ? 'Reset the filters or add a transaction.' : 'Add your first real transaction to this profile.'}</p><div className="app-placeholder-actions"><button type="button" className="app-btn primary" onClick={() => setFormTransaction('new')} disabled={accounts.length === 0}>Add transaction</button><button type="button" className="app-btn" onClick={resetFilters}>Reset filters</button></div></div> : <>
        <div className="tx-table-wrap app-card"><table className="tx-table"><caption className="tx-sr-only">Transactions for {profile.currentProfile.name}</caption><thead>{table.getHeaderGroups().map((group) => <tr key={group.id}>{group.headers.map((header) => { const sorted = header.column.getIsSorted(); return <th key={header.id} scope="col" aria-sort={sorted ? sorted === 'asc' ? 'ascending' : 'descending' : undefined}>{header.isPlaceholder ? null : header.column.getCanSort() ? <button type="button" className="tx-sort" onClick={header.column.getToggleSortingHandler()}>{flexRender(header.column.columnDef.header, header.getContext())}<span aria-hidden="true">{sorted === 'asc' ? '↑' : sorted === 'desc' ? '↓' : '↕'}</span></button> : flexRender(header.column.columnDef.header, header.getContext())}</th>; })}</tr>)}</thead><tbody>{table.getRowModel().rows.map((row) => <tr key={row.id} className={row.original.deleted_at ? 'deleted' : ''}>{row.getVisibleCells().map((cell) => <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>)}</tbody></table></div>
        <div className="tx-cards" aria-label="Transactions">{table.getRowModel().rows.map((row) => { const item = row.original; const category = categoryFor(categories, item.category_id); const name = item.merchant || item.raw_description; const titleId = `tx-card-title-${item.id}`; return <article className={`tx-card app-card ${item.deleted_at ? 'deleted' : ''}`} key={item.id} aria-labelledby={titleId}><header><label className="tx-card-select"><input type="checkbox" checked={row.getIsSelected()} onChange={row.getToggleSelectedHandler()} disabled={Boolean(item.deleted_at)} /><span className="tx-sr-only">Select {name}</span></label><button type="button" className="tx-card-title" onClick={() => setDetailTransaction(item)} aria-label={`Open details for ${name}`}><strong id={titleId}>{name}</strong><small>{item.date} · {nameForAccount(accounts, item.account_id)}</small></button><span className={`tx-amount ${item.amount_cents < 0 ? 'credit' : ''}`}>{formatCad(item.amount_cents)}</span></header><div className="tx-card-meta"><span>{transactionTypeLabel(item.type)}</span><span>{item.included_in_spending ? 'Included in spending' : 'Excluded from spending'}</span>{item.deleted_at && <span>In trash</span>}</div><label className="tx-card-category"><span>{category ? <><CategoryIcon name={category.icon} />{category.name}</> : 'Category'}</span><select value={item.category_id ?? ''} onChange={(event) => updateCategory(item, event.target.value)} disabled={Boolean(item.deleted_at)} aria-label={`Category for ${name}`}><option value="">Uncategorized</option>{categories.map((option) => <option value={option.id} key={option.id}>{option.name}</option>)}</select></label><footer><button type="button" aria-label={`Open details for ${name}`} onClick={() => setDetailTransaction(item)}>Details</button><button type="button" aria-label={`Edit ${name}`} onClick={() => setFormTransaction(item)} disabled={Boolean(item.deleted_at)}>Edit</button>{item.deleted_at ? <button type="button" aria-label={`Restore ${name}`} onClick={() => restore(item)}>Restore</button> : <button type="button" className="danger" aria-label={`Move ${name} to trash`} onClick={() => setDeleteTransaction(item)}>Trash</button>}</footer></article>; })}</div>
        <nav className="tx-pagination" aria-label="Transaction pages"><span>Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()} · {table.getPrePaginationRowModel().rows.length} transactions</span><label>Rows per page<select value={table.getState().pagination.pageSize} onChange={(event) => table.setPageSize(Number(event.target.value))}><option value="10">10</option><option value="20">20</option><option value="50">50</option></select></label><button type="button" className="app-btn" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>Previous</button><button type="button" className="app-btn" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>Next</button></nav>
      </>}

      {formTransaction && <TransactionFormDialog accounts={accounts} categories={categories} initial={formTransaction === 'new' ? null : formTransaction} onClose={() => setFormTransaction(null)} onCreate={(body) => createMutation.mutateAsync(body)} onUpdate={(id, body) => updateMutation.mutateAsync({ id, body })} />}
      {detailTransaction && <TransactionDetailDialog profileId={profileId} transaction={detailTransaction} categories={categories} onClose={() => setDetailTransaction(null)} onEdit={(transaction) => { setDetailTransaction(null); setFormTransaction(transaction); }} />}
      {deleteTransaction && <ConfirmDialog title="Move transaction to trash?" description={`${deleteTransaction.merchant || deleteTransaction.raw_description} can be restored later.`} confirmLabel="Move to trash" pending={deleteMutation.isPending} danger onCancel={() => setDeleteTransaction(null)} onConfirm={async () => { try { await deleteMutation.mutateAsync(deleteTransaction.id); setLiveMessage('Transaction moved to trash.'); } catch (cause) { setActionError(`${cause instanceof ApiError ? cause.message : 'Move to trash failed.'} Open Trash again to retry.`); } finally { setDeleteTransaction(null); } }} />}
      {confirmBulk && <ConfirmDialog title={`Update ${selectedIds.length} transaction${selectedIds.length === 1 ? '' : 's'}?`} description={bulkAction === 'categorize' ? `Set category to ${categoryFor(categories, bulkCategory ? Number(bulkCategory) : null)?.name ?? 'Uncategorized'}.` : bulkAction === 'include' ? 'Include the selected transactions in spending totals.' : `Exclude them from spending: ${bulkReason.trim()}`} confirmLabel={`Update ${selectedIds.length}`} pending={bulkMutation.isPending} onCancel={() => setConfirmBulk(false)} onConfirm={runBulk} />}
    </section>
  );
}

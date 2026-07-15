// Account wire types — mirror apps/api/app/schemas/account.py exactly.

export type IssuerCode = 'TD' | 'AMEX' | 'CIBC' | 'OTHER';

export interface Account {
  id: number;
  profile_id: number;
  issuer: IssuerCode;
  display_name: string;
  color: string;
  last4: string | null;
  currency: 'CAD';
  account_fingerprint: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface AccountCreate {
  issuer: IssuerCode;
  display_name: string;
  color: string;
  last4?: string | null;
  currency?: 'CAD';
}

export interface AccountUpdate {
  issuer?: IssuerCode;
  display_name?: string;
  color?: string;
  last4?: string | null;
  is_archived?: boolean;
}

export const ISSUERS: { code: IssuerCode; label: string }[] = [
  { code: 'TD', label: 'TD' },
  { code: 'AMEX', label: 'American Express' },
  { code: 'CIBC', label: 'CIBC' },
  { code: 'OTHER', label: 'Other' },
];

export const CARD_COLORS = [
  '#4f6bff',
  '#12805c',
  '#2f6fed',
  '#7c5cff',
  '#ef4444',
  '#f97316',
  '#eab308',
  '#0ea5e9',
  '#ec4899',
  '#64748b',
];

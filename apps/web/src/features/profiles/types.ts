// Profile wire types — mirror the backend contract exactly (snake_case fields,
// integer ids). Source: apps/api/app/schemas/profile.py.

export interface Profile {
  id: number;
  name: string;
  base_currency: 'CAD';
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProfileCreate {
  name: string;
  base_currency?: 'CAD';
}

export interface ProfileUpdate {
  name?: string;
  is_archived?: boolean;
}

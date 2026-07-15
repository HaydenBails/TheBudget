import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useProfiles } from './api';
import type { Profile } from './types';

const STORAGE_KEY = 'st-current-profile';

interface ProfileContextValue {
  profiles: Profile[];
  currentProfile: Profile | null;
  currentProfileId: number | null;
  selectProfile: (id: number) => void;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
}

const Ctx = createContext<ProfileContextValue | null>(null);

function readStored(): number | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  const n = raw ? Number(raw) : NaN;
  return Number.isFinite(n) ? n : null;
}

export function ProfileProvider({ children }: { children: ReactNode }) {
  const { data, isLoading, isError, error } = useProfiles(false);
  const profiles = useMemo(() => data ?? [], [data]);
  const [currentProfileId, setCurrentProfileId] = useState<number | null>(readStored);

  // Reconcile selection whenever the active profile list changes.
  useEffect(() => {
    if (isLoading) return;
    const exists = currentProfileId != null && profiles.some((p) => p.id === currentProfileId);
    if (!exists) {
      const next = profiles[0]?.id ?? null;
      setCurrentProfileId(next);
      if (next == null) localStorage.removeItem(STORAGE_KEY);
      else localStorage.setItem(STORAGE_KEY, String(next));
    }
  }, [profiles, currentProfileId, isLoading]);

  const value = useMemo<ProfileContextValue>(() => {
    const selectProfile = (id: number) => {
      setCurrentProfileId(id);
      localStorage.setItem(STORAGE_KEY, String(id));
    };
    const currentProfile = profiles.find((p) => p.id === currentProfileId) ?? null;
    return { profiles, currentProfile, currentProfileId, selectProfile, isLoading, isError, error };
  }, [profiles, currentProfileId, isLoading, isError, error]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useCurrentProfile(): ProfileContextValue {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useCurrentProfile must be used within ProfileProvider');
  return ctx;
}

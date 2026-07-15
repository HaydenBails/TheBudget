import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

export type ThemeMode = 'light' | 'dark';

interface ThemeCtx {
  theme: ThemeMode;
  toggle: () => void;
  set: (m: ThemeMode) => void;
}

const Ctx = createContext<ThemeCtx | null>(null);

function initialTheme(): ThemeMode {
  const stored = localStorage.getItem('st-theme');
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<ThemeMode>(initialTheme);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('st-theme', theme);
  }, [theme]);

  const value = useMemo<ThemeCtx>(
    () => ({
      theme,
      toggle: () => setTheme((t) => (t === 'light' ? 'dark' : 'light')),
      set: setTheme,
    }),
    [theme],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTheme(): ThemeCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}

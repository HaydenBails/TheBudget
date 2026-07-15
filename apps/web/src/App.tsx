import { Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom';
import { directionById, directions } from './directions/registry';
import type { ScreenKey } from './directions/types';
import { useTheme } from './theme';
import { Landing } from './Landing';
import { AppShell } from './app/AppShell';

const SCREENS: { key: ScreenKey; label: string }[] = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'transactions', label: 'Transactions' },
  { key: 'review', label: 'Review' },
];

function Switcher({ directionId, screen }: { directionId: string; screen: ScreenKey }) {
  const nav = useNavigate();
  const { theme, toggle } = useTheme();
  return (
    <div className="harness-switcher" role="navigation" aria-label="Prototype switcher">
      <button className="harness-home" onClick={() => nav('/')} title="Compare all directions">
        ← Compare
      </button>
      <span className="harness-sep" />
      <div className="harness-group" role="group" aria-label="Design direction">
        {directions.map((d) => (
          <button
            key={d.meta.id}
            className={d.meta.id === directionId ? 'active' : ''}
            onClick={() => nav(`/${d.meta.id}/${screen}`)}
          >
            {d.meta.name}
          </button>
        ))}
      </div>
      <span className="harness-sep" />
      <div className="harness-group" role="group" aria-label="Screen">
        {SCREENS.map((s) => (
          <button
            key={s.key}
            className={s.key === screen ? 'active' : ''}
            onClick={() => nav(`/${directionId}/${s.key}`)}
          >
            {s.label}
          </button>
        ))}
      </div>
      <span className="harness-sep" />
      <button className="harness-theme" onClick={toggle} title="Toggle light/dark">
        {theme === 'light' ? '🌙 Dark' : '☀️ Light'}
      </button>
    </div>
  );
}

function DirectionScreen() {
  const { directionId = '', screen = 'dashboard' } = useParams();
  const direction = directionById[directionId];
  if (!direction) return <Navigate to="/" replace />;

  const key = (['dashboard', 'transactions', 'review'].includes(screen) ? screen : 'dashboard') as ScreenKey;
  const Screen =
    key === 'dashboard' ? direction.Dashboard : key === 'transactions' ? direction.Transactions : direction.Review;

  return (
    <div className="harness-root">
      <Screen />
      <Switcher directionId={directionId} screen={key} />
    </div>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      {/* Production application shell (FE-02), separate from the prototype harness. */}
      <Route path="/app/*" element={<AppShell />} />
      <Route path="/:directionId/:screen" element={<DirectionScreen />} />
      <Route path="/:directionId" element={<DirectionRedirect />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function DirectionRedirect() {
  const { directionId = '' } = useParams();
  return <Navigate to={`/${directionId}/dashboard`} replace />;
}

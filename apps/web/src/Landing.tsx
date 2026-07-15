import { Link } from 'react-router-dom';
import { directions } from './directions/registry';
import { useTheme } from './theme';
import { totalSpendingCents, CURRENT_YM } from './lib/derived';
import { formatDollarsAbs } from './lib/format';
import './Landing.css';

export function Landing() {
  const { theme, toggle } = useTheme();
  const spend = totalSpendingCents(CURRENT_YM);

  return (
    <div className="landing">
      <header className="landing-top">
        <div className="landing-brand">
          <span className="landing-logo">◔</span>
          <span>Spending Tracker</span>
          <span className="landing-badge">Stage 1 · UI directions</span>
        </div>
        <button className="landing-themebtn" onClick={toggle}>
          {theme === 'light' ? '🌙 Dark' : '☀️ Light'}
        </button>
      </header>

      <section className="landing-hero">
        <h1>Three directions, one dataset.</h1>
        <p>
          Compare three interactive UI directions for the spending tracker. Each renders the same
          Dashboard, Transactions, and Review Categories screens from an identical synthetic dataset
          ({formatDollarsAbs(spend)} of spending this month) — so the design is judged on its own
          merits, not different numbers. Toggle light/dark on every screen. Pick one to move forward.
        </p>
      </section>

      <section className="landing-grid">
        {directions.map((d) => (
          <article className="landing-card" key={d.meta.id} style={{ ['--accent' as string]: d.meta.accent }}>
            <div className="landing-card-swatch" />
            <div className="landing-card-body">
              <h2>{d.meta.name}</h2>
              <p className="landing-card-tag">{d.meta.tagline}</p>
              <p className="landing-card-desc">{d.meta.description}</p>
              <div className="landing-card-links">
                <Link className="primary" to={`/${d.meta.id}/dashboard`}>
                  Open dashboard
                </Link>
                <Link to={`/${d.meta.id}/transactions`}>Transactions</Link>
                <Link to={`/${d.meta.id}/review`}>Review</Link>
              </div>
            </div>
          </article>
        ))}
      </section>

      <footer className="landing-foot">
        Synthetic data only — no real statements. See <code>docs/decisions/0002-ui-directions.md</code>.
      </footer>
    </div>
  );
}

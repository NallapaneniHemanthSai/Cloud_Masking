// App shell: header (app name + live backend status) + left nav + routed page outlet.
import { NavLink, Outlet } from 'react-router-dom';
import { useSystem } from '../context/SystemContext';

const NAV: { to: string; label: string }[] = [
  { to: '/', label: 'Dashboard' },
  { to: '/models', label: 'Models' },
  { to: '/predict', label: 'Predict' },
  { to: '/evaluate', label: 'Evaluate' },
  { to: '/comparison', label: 'Comparison' },
  { to: '/upload', label: 'Upload' },
  { to: '/history', label: 'History' },
  { to: '/metrics', label: 'Metrics' },
  { to: '/map', label: 'Map' },
  { to: '/system', label: 'System' },
];

const APP_NAME = (import.meta.env.VITE_APP_NAME as string | undefined) || 'Cloud Masking';

export function Layout() {
  const { version, health, error } = useSystem();
  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">◐</span>
          <span className="brand-name">{APP_NAME}</span>
          <span className="brand-sub">Sentinel-2 cloud segmentation</span>
        </div>
        <div className="header-status">
          {error ? (
            <span className="badge badge-pending" title={error.detail}>backend unreachable</span>
          ) : (
            <>
              <span className="badge badge-real" title="Backend API version">
                API v{version?.app_version ?? '…'}
              </span>
              <span
                className={`badge ${health?.torch_available ? 'badge-real' : 'badge-deferred'}`}
                title={`device: ${health?.device ?? '?'}`}
              >
                {health ? `${health.device}${health.torch_available ? '' : ' (no torch)'}` : '…'}
              </span>
            </>
          )}
        </div>
      </header>
      <div className="app-body">
        <nav className="side-nav" aria-label="Primary">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => (isActive ? 'active' : '')}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <main className="app-main">
          <Outlet />
        </main>
      </div>
      <footer className="app-footer">
        Results shown here from <code>/train</code> and <code>/evaluate</code> are
        <span className="badge badge-synthetic">SYNTHETIC</span> validation-only — not benchmarks. Real
        model quality is measured offline (bounded, not AC-4).
      </footer>
    </div>
  );
}

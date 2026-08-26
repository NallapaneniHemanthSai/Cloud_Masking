import { Link } from 'react-router-dom';
import { useSystem } from '../context/SystemContext';
import { useApiResource } from '../hooks/useApiResource';
import { getMetrics, getModels } from '../services/api';
import type { MetricsResponse, ModelsResponse } from '../services/types';
import { Card, ErrorState, Loading, MetricTile, RegimeBadge } from '../components/ui';
import { ClassLegend } from '../components/ClassViz';

export function Dashboard() {
  const { version, health, loading, error, reload } = useSystem();
  const models = useApiResource<ModelsResponse>(getModels, []);
  const metrics = useApiResource<MetricsResponse>(getMetrics, []);

  return (
    <div className="page">
      <div className="page-head">
        <h1>Project overview</h1>
        <p className="muted">
          Multispectral Sentinel-2 cloud segmentation — thin-cloud-aware Attention U-Net. This dashboard
          drives the backend API's core flows.
        </p>
      </div>

      {loading && <Loading label="Contacting backend…" />}
      {error && <ErrorState error={error} onRetry={reload} />}

      {!loading && !error && (
        <div className="tiles">
          <MetricTile label="API version" value={version?.app_version ?? '—'} />
          <MetricTile label="Device" value={health?.device ?? '—'} hint={health?.torch_available ? 'torch available' : 'torch unavailable'} />
          <MetricTile label="Architectures" value={models.data?.architectures.length ?? '…'} />
          <MetricTile label="API requests" value={metrics.data?.total_requests ?? '…'} hint={`${metrics.data?.total_errors ?? 0} errors`} />
        </div>
      )}

      <div className="grid-2">
        <Card title="Honesty & data status">
          <ul className="bullets">
            <li>
              <RegimeBadge regime="SYNTHETIC" /> <code>/train</code> and <code>/evaluate</code> are bounded
              synthetic validation only — never benchmarks.
            </li>
            <li>
              <RegimeBadge regime="REAL" /> The one real experiment (bounded 32-sample CloudSEN12+, 3 seeds)
              concluded <strong>MIXED</strong>: thin-cloud improved, cloud-shadow regressed. See{' '}
              <Link to="/comparison">Comparison</Link>.
            </li>
            <li>
              <RegimeBadge regime="NOT_YET_MEASURED" /> Formal AC-4 KPI benchmarks.
            </li>
            <li>
              <RegimeBadge regime="DEFERRED" /> Pixel-mask rendering & geo-overlay (the API returns class
              counts, not mask pixels).
            </li>
          </ul>
        </Card>
        <Card title="CloudSEN12 classes (M5 palette)">
          <ClassLegend />
          <p className="muted small">
            Colours and names are reused verbatim from the backend visualization/evaluation layers.
          </p>
        </Card>
      </div>

      <Card title="Core flows">
        <div className="quick-links">
          <Link className="btn" to="/models">Browse models</Link>
          <Link className="btn" to="/predict">Run a prediction</Link>
          <Link className="btn" to="/evaluate">Evaluate (synthetic)</Link>
          <Link className="btn" to="/upload">Upload a scene</Link>
          <Link className="btn" to="/history">View history</Link>
          <Link className="btn" to="/metrics">Telemetry</Link>
        </div>
      </Card>
    </div>
  );
}

import { useApiResource } from '../hooks/useApiResource';
import { getMetrics } from '../services/api';
import type { MetricsResponse } from '../services/types';
import { Card, EmptyState, ErrorState, Loading, MetricTile } from '../components/ui';
import { fmtSeconds } from '../utils/format';

export function Metrics() {
  const { data, loading, error, reload } = useApiResource<MetricsResponse>(getMetrics, []);

  return (
    <div className="page">
      <div className="page-head">
        <h1>Telemetry</h1>
        <p className="muted">In-process request metrics from the backend middleware (<code>/metrics</code>).</p>
      </div>

      {loading && <Loading />}
      {error && <ErrorState error={error} onRetry={reload} />}

      {data && (
        <>
          <div className="tiles">
            <MetricTile label="Uptime" value={`${Math.round(data.uptime_seconds)} s`} />
            <MetricTile label="Total requests" value={data.total_requests} />
            <MetricTile label="Total errors" value={data.total_errors} />
            <MetricTile label="Routes seen" value={data.routes.length} />
          </div>
          <Card title="Per-route latency" actions={<button className="btn" onClick={reload}>Refresh</button>}>
            {data.routes.length === 0 ? (
              <EmptyState message="No requests recorded yet." />
            ) : (
              <table className="table">
                <thead>
                  <tr><th>route</th><th>count</th><th>errors</th><th>avg</th><th>last</th></tr>
                </thead>
                <tbody>
                  {data.routes.map((r) => (
                    <tr key={r.route}>
                      <td className="mono">{r.route}</td>
                      <td>{r.count}</td>
                      <td>{r.error_count}</td>
                      <td className="mono">{fmtSeconds(r.avg_seconds)}</td>
                      <td className="mono">{fmtSeconds(r.last_seconds)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </>
      )}
    </div>
  );
}

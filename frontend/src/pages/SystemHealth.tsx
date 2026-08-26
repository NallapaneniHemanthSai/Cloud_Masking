import { useSystem } from '../context/SystemContext';
import { Card, ErrorState, Loading } from '../components/ui';

export function SystemHealth() {
  const { version, health, loading, error, reload } = useSystem();

  return (
    <div className="page">
      <div className="page-head">
        <h1>System &amp; versions</h1>
        <p className="muted">Live component versions and runtime health from the backend.</p>
      </div>

      {loading && <Loading />}
      {error && <ErrorState error={error} onRetry={reload} />}

      {health && (
        <Card title="Health" actions={<button className="btn" onClick={reload}>Refresh</button>}>
          <dl className="kv wide">
            <dt>status</dt><dd>{health.status}</dd>
            <dt>device</dt><dd>{health.device}</dd>
            <dt>torch available</dt><dd>{String(health.torch_available)}</dd>
            <dt>database</dt><dd className="mono">{health.database}</dd>
          </dl>
        </Card>
      )}

      {version && (
        <Card title="Component versions">
          <dl className="kv wide">
            <dt>app (API)</dt><dd>{version.app_version}</dd>
            <dt>model (baseline)</dt><dd>{version.model_version}</dd>
            <dt>model (improved)</dt><dd>{version.improved_model_version}</dd>
            <dt>preprocessing</dt><dd>{version.preprocessing_version}</dd>
            <dt>visualization</dt><dd>{version.visualization_version}</dd>
            <dt>training</dt><dd>{version.training_version}</dd>
            <dt>evaluation</dt><dd>{version.evaluation_version}</dd>
            <dt>failure analysis</dt><dd>{version.failure_analysis_version}</dd>
            <dt>comparison</dt><dd>{version.comparison_version}</dd>
            <dt>dataset manifest</dt><dd>{version.dataset_manifest_version}</dd>
            <dt>python</dt><dd>{version.python}</dd>
            <dt>torch</dt><dd>{version.torch ?? 'not installed'}</dd>
          </dl>
        </Card>
      )}
    </div>
  );
}

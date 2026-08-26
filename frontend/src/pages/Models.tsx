import { useApiResource } from '../hooks/useApiResource';
import { getModels } from '../services/api';
import type { ModelsResponse } from '../services/types';
import { Card, EmptyState, ErrorState, Loading } from '../components/ui';
import { fmtDate, fmtInt, shortHash } from '../utils/format';

export function Models() {
  const { data, loading, error, reload } = useApiResource<ModelsResponse>(getModels, []);

  return (
    <div className="page">
      <div className="page-head">
        <h1>Models</h1>
        <p className="muted">Architectures from the backend registry (M6) + versions registered in the DB.</p>
      </div>

      {loading && <Loading />}
      {error && <ErrorState error={error} onRetry={reload} />}

      {data && (
        <>
          <Card title={`Architectures (${data.architectures.length})`}>
            {data.architectures.length === 0 ? (
              <EmptyState />
            ) : (
              <div className="model-grid">
                {data.architectures.map((m) => (
                  <div key={m.architecture} className="model-card">
                    <div className="model-title">
                      <strong>{m.architecture}</strong> <span className="muted">v{m.version}</span>
                      {m.improves_over && <span className="badge badge-real">improves {m.improves_over}</span>}
                    </div>
                    <p className="muted small">{m.description || '—'}</p>
                    <dl className="kv">
                      <dt>aliases</dt><dd>{m.aliases.join(', ') || '—'}</dd>
                      <dt>input channels</dt><dd>{m.supported_input_channels.join(', ') || '—'}</dd>
                      <dt>output classes</dt><dd>{m.supported_output_classes.join(', ') || '—'}</dd>
                    </dl>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card title={`Registered versions (${data.registered_versions.length})`}>
            {data.registered_versions.length === 0 ? (
              <EmptyState message="No model versions registered yet." />
            ) : (
              <table className="table">
                <thead>
                  <tr><th>model_id</th><th>arch</th><th>version</th><th>params</th><th>config_hash</th><th>created</th></tr>
                </thead>
                <tbody>
                  {data.registered_versions.map((v) => (
                    <tr key={v.id}>
                      <td className="mono">{v.model_id}</td>
                      <td>{v.architecture}</td>
                      <td>{v.version}</td>
                      <td className="mono">{fmtInt(v.parameter_count)}</td>
                      <td className="mono">{shortHash(v.config_hash)}</td>
                      <td>{fmtDate(v.created_at)}</td>
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

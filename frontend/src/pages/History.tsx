import { useApiResource } from '../hooks/useApiResource';
import { getHistory } from '../services/api';
import type { HistoryResponse } from '../services/types';
import { Card, EmptyState, ErrorState, Loading, RegimeBadge } from '../components/ui';
import { fmtDate } from '../utils/format';

type Row = Record<string, unknown>;

function HistoryTable({ rows, columns }: { rows: Row[]; columns: string[] }) {
  if (rows.length === 0) return <EmptyState message="No records yet." />;
  return (
    <table className="table">
      <thead>
        <tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            {columns.map((c) => {
              const v = r[c];
              if (c === 'data_regime' && typeof v === 'string') return <td key={c}><RegimeBadge regime={v} /></td>;
              if (c === 'created_at') return <td key={c}>{fmtDate(v as string)}</td>;
              return <td key={c} className="mono">{v === null || v === undefined ? '—' : String(v)}</td>;
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function History() {
  const { data, loading, error, reload } = useApiResource<HistoryResponse>(() => getHistory(50), []);

  return (
    <div className="page">
      <div className="page-head">
        <h1>History</h1>
        <p className="muted">Persisted training / prediction / evaluation / upload records (SQLite).</p>
      </div>

      {loading && <Loading />}
      {error && <ErrorState error={error} onRetry={reload} />}

      {data && (
        <>
          <Card title={`Training runs (${data.training_runs.length})`} actions={<button className="btn" onClick={reload}>Refresh</button>}>
            <HistoryTable rows={data.training_runs} columns={['run_id', 'architecture', 'data_regime', 'device', 'epochs', 'duration_seconds', 'final_loss', 'created_at']} />
          </Card>
          <Card title={`Predictions (${data.predictions.length})`}>
            <HistoryTable rows={data.predictions} columns={['prediction_id', 'architecture', 'data_regime', 'device', 'output_shape', 'created_at']} />
          </Card>
          <Card title={`Evaluations (${data.evaluations.length})`}>
            <HistoryTable rows={data.evaluations} columns={['evaluation_id', 'dataset', 'split', 'data_regime', 'macro_iou', 'thin_cloud_iou', 'created_at']} />
          </Card>
          <Card title={`Uploads (${data.uploads.length})`}>
            <HistoryTable rows={data.uploads} columns={['upload_id', 'filename', 'content_hash', 'size_bytes', 'created_at']} />
          </Card>
        </>
      )}
    </div>
  );
}

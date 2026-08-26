import { useApiResource } from '../hooks/useApiResource';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { getLineage, getStatus, recoverEvent, runPipeline } from '../services/api';
import type { LineageResponse, PipelineRequest, PipelineResponse, RecoverResponse, StatusResponse } from '../services/types';
import { Card, EmptyState, ErrorState, Loading, MetricTile, RegimeBadge } from '../components/ui';
import { fmtDate } from '../utils/format';

export function Status() {
  const status = useApiResource<StatusResponse>(getStatus, []);
  const lineage = useApiResource<LineageResponse>(() => getLineage(25), []);
  const pipeline = useAsyncAction<Partial<PipelineRequest>, PipelineResponse>(runPipeline);
  const recovery = useAsyncAction<string, RecoverResponse>((id) => recoverEvent(id, 'recovered via UI'));

  const refresh = () => {
    status.reload();
    lineage.reload();
  };
  const onRun = async (inject: boolean) => {
    await pipeline.run({ seed: 0, with_prediction: false, inject_guardrail_failure: inject });
    refresh();
  };
  const onRecover = async (eventId: string) => {
    await recovery.run(eventId);
    refresh();
  };

  const s = status.data;

  return (
    <div className="page">
      <div className="page-head">
        <h1>System status &amp; integration</h1>
        <p className="muted">
          End-to-end pipeline, <strong>degraded mode + recovery</strong>, and NT-5 lineage. Runs are
          <RegimeBadge regime="SYNTHETIC" /> (or <RegimeBadge regime="DEMO" /> when a guardrail failure is
          injected to exercise degraded mode) — never real-data metrics.
        </p>
      </div>

      {status.loading && <Loading />}
      {status.error && <ErrorState error={status.error} onRetry={status.reload} />}

      {s && (
        <>
          <div className={`state ${s.degraded ? 'error' : ''}`} role="status">
            <strong>System is {s.degraded ? 'DEGRADED' : 'operational'}.</strong>{' '}
            {s.degraded
              ? 'A guardrail detected an aggregate hiding a failing subgroup — affected results are labelled and held from silent use until recovery.'
              : 'All guardrails passing.'}
          </div>

          <div className="tiles">
            <MetricTile label="Status" value={<RegimeBadge regime={s.degraded ? 'DEFERRED' : 'REAL'} title={s.status} />} hint={s.status} />
            <MetricTile label="Active degraded events" value={s.active_degraded_events.length} />
            <MetricTile label="Total events" value={s.event_count} />
            <MetricTile label="Lineage nodes" value={s.lineage_count} />
          </div>

          <Card
            title="End-to-end pipeline"
            actions={
              <>
                <button className="btn primary" onClick={() => void onRun(false)} disabled={pipeline.pending}>
                  {pipeline.pending ? 'Running…' : 'Run (healthy)'}
                </button>
                <button className="btn" onClick={() => void onRun(true)} disabled={pipeline.pending}>
                  Run (inject degraded · DEMO)
                </button>
              </>
            }
          >
            {pipeline.error && <ErrorState error={pipeline.error} />}
            {!pipeline.result && <p className="muted">Run the pipeline (evaluate → guardrail → lineage).</p>}
            {pipeline.result && (
              <dl className="kv">
                <dt>data regime</dt><dd><RegimeBadge regime={pipeline.result.data_regime} /></dd>
                <dt>guardrail passed</dt><dd>{String(pipeline.result.guardrail_passed)}</dd>
                {pipeline.result.guardrail_reasons.length > 0 && (
                  <>
                    <dt>reasons</dt>
                    <dd>{pipeline.result.guardrail_reasons.map((r, i) => <div key={i} className="small">{r}</div>)}</dd>
                  </>
                )}
                <dt>lineage recorded</dt><dd>{pipeline.result.lineage.length} node(s)</dd>
                <dt>note</dt><dd className="small">{pipeline.result.note}</dd>
              </dl>
            )}
          </Card>

          <Card title={`Active degraded events (${s.active_degraded_events.length})`} actions={<button className="btn" onClick={refresh}>Refresh</button>}>
            {s.active_degraded_events.length === 0 ? (
              <EmptyState message="No active degraded events." />
            ) : (
              <table className="table">
                <thead><tr><th>event</th><th>subject</th><th>reason</th><th>action</th></tr></thead>
                <tbody>
                  {s.active_degraded_events.map((e) => (
                    <tr key={e.event_id}>
                      <td className="mono">{e.event_id}</td>
                      <td className="mono">{e.subject}</td>
                      <td className="small">{e.reason}</td>
                      <td>
                        <button className="btn" onClick={() => void onRecover(e.event_id)} disabled={recovery.pending}>
                          {recovery.pending ? 'Recovering…' : 'Recover'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </>
      )}

      <Card title="Lineage (NT-5)">
        {lineage.loading && <Loading />}
        {lineage.error && <ErrorState error={lineage.error} onRetry={lineage.reload} />}
        {lineage.data && (lineage.data.nodes.length === 0 ? (
          <EmptyState message="No lineage recorded yet — run the pipeline." />
        ) : (
          <table className="table">
            <thead><tr><th>lineage_id</th><th>type</th><th>parent</th><th>content_hash</th><th>created</th></tr></thead>
            <tbody>
              {lineage.data.nodes.map((n, i) => (
                <tr key={i}>
                  <td className="mono">{String(n['lineage_id'])}</td>
                  <td>{String(n['artifact_type'])}</td>
                  <td className="mono">{n['parent_lineage_id'] ? String(n['parent_lineage_id']) : '—'}</td>
                  <td className="mono">{String(n['content_hash']).slice(0, 12)}</td>
                  <td>{fmtDate(n['created_at'] as string)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ))}
      </Card>
    </div>
  );
}

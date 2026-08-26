import { useApiResource } from '../hooks/useApiResource';
import { getAcceptance } from '../services/api';
import type { AcceptanceResponse } from '../services/types';
import { Card, ErrorState, Loading, MetricTile, RegimeBadge } from '../components/ui';

function b(v: unknown): string {
  return String(v);
}

export function Acceptance() {
  const { data, loading, error, reload } = useApiResource<AcceptanceResponse>(getAcceptance, []);

  return (
    <div className="page">
      <div className="page-head">
        <h1>Acceptance harness (D5)</h1>
        <p className="muted">
          The five mandatory negative tests (NT-1..NT-5) on <RegimeBadge regime="SYNTHETIC" /> fixtures.
          Real KPI/AC-4 acceptance is <RegimeBadge regime="NOT_YET_MEASURED" /> — never fabricated; the M11
          real-data conclusion remains <strong>MIXED</strong>.
        </p>
      </div>

      {loading && <Loading label="Running acceptance harness…" />}
      {error && <ErrorState error={error} onRetry={reload} />}

      {data && (
        <>
          <div className={`state ${data.safety_passed ? '' : 'error'}`} role="status">
            <strong>Safety properties: {data.safety_passed ? 'PASS' : 'FAIL'}.</strong>{' '}
            Overall: <code>{data.overall}</code>. {data.failed_nts.length > 0 && `Failed: ${data.failed_nts.join(', ')}.`}
          </div>

          <div className="tiles">
            <MetricTile label="Safety" value={<RegimeBadge regime={data.safety_passed ? 'REAL' : 'DEFERRED'} title={data.overall} />} hint={data.safety_passed ? 'all NTs pass' : 'NT failure'} />
            <MetricTile label="KPI acceptance" value={<RegimeBadge regime="NOT_YET_MEASURED" />} hint="needs real AC-4 data" />
            <MetricTile label="Negative tests" value={data.nt_results.length} />
            <MetricTile label="Version" value={data.acceptance_version} hint={data.content_hash.slice(0, 10)} />
          </div>

          <Card title="Negative tests (NT-1..NT-5)" actions={<button className="btn" onClick={reload}>Re-run</button>}>
            <table className="table">
              <thead>
                <tr><th>NT</th><th>name</th><th>owner</th><th>passed</th><th>pass fired</th><th>fail fired</th><th>action on fail</th></tr>
              </thead>
              <tbody>
                {data.nt_results.map((nt, i) => {
                  const pc = (nt['pass_case'] as Record<string, unknown>) || {};
                  const fc = (nt['fail_case'] as Record<string, unknown>) || {};
                  const passed = nt['passed'] === true;
                  return (
                    <tr key={i} className={passed ? '' : 'row-tradeoff'}>
                      <td className="mono">{b(nt['nt_id'])}</td>
                      <td>{b(nt['name'])}</td>
                      <td className="small">{b(nt['owner'])}</td>
                      <td><RegimeBadge regime={passed ? 'REAL' : 'DEFERRED'} title={passed ? 'pass' : 'fail'} /></td>
                      <td className="mono">{b(pc['triggered'])}</td>
                      <td className="mono">{b(fc['triggered'])}</td>
                      <td className="small">{b(fc['action'])}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>

          <div className="grid-2">
            <Card title="AC coverage">
              <table className="table">
                <thead><tr><th>AC</th><th>status</th></tr></thead>
                <tbody>
                  {data.ac_coverage.map((a, i) => (
                    <tr key={i}><td className="mono">{b(a['ac'])}</td><td>{b(a['status'])}</td></tr>
                  ))}
                </tbody>
              </table>
            </Card>
            <Card title="KPI status">
              <p className="muted small">All formal KPIs are <RegimeBadge regime="NOT_YET_MEASURED" /> (no real AC-4 dataset).</p>
              <div className="mono small">{data.kpi_status.map((k) => b(k['kpi'])).join(' · ')}</div>
            </Card>
          </div>

          <Card title="Coverage / test inventory">
            <p className="muted small">
              Line-coverage %: <RegimeBadge regime="DEFERRED" /> (pytest-cov not installed). NT/harness
              inventory below.
            </p>
            <pre className="json">{JSON.stringify(data.coverage, null, 2)}</pre>
          </Card>
        </>
      )}
    </div>
  );
}

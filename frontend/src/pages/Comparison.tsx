import { REAL_M11, type SeedDeltas } from '../data/realComparison';
import { Card, MetricTile, RegimeBadge } from '../components/ui';
import { classColor, classLabel } from '../utils/colors';

const CLASS_KEYS: (keyof SeedDeltas)[] = ['clear', 'thick_cloud', 'thin_cloud', 'cloud_shadow'];

function delta(v: number): { text: string; cls: string } {
  const text = `${v >= 0 ? '+' : ''}${v.toFixed(3)}`;
  return { text, cls: v > 0.001 ? 'pos' : v < -0.001 ? 'neg' : 'flat' };
}

export function Comparison() {
  return (
    <div className="page">
      <div className="page-head">
        <h1>U-Net vs Attention U-Net — real comparison</h1>
        <p className="muted">
          <RegimeBadge regime="REAL" /> Bounded first experiment on real CloudSEN12+ — <strong>not</strong>{' '}
          the AC-4 benchmark. Verdict: <strong>{REAL_M11.conclusion}</strong>. Transcribed verbatim from{' '}
          <code>{REAL_M11.source}</code>; no metric is invented and the conclusion is not reinterpreted.
        </p>
      </div>

      <div className="tiles">
        <MetricTile label="Thin-cloud IoU Δ (mean)" value={`+${REAL_M11.thinCloud.meanDeltaIoU.toFixed(3)}`} hint="improved every seed" />
        <MetricTile label="Cloud-shadow" value="regressed" hint="consistently (small)" />
        <MetricTile label="Params" value={`×${(REAL_M11.params.attention_unet / REAL_M11.params.unet).toFixed(3)}`} hint={`${REAL_M11.params.unet} → ${REAL_M11.params.attention_unet}`} />
        <MetricTile label="Seeds" value={REAL_M11.seeds} hint="no formal significance test" />
      </div>

      <Card title="Per-class ΔIoU (Attention U-Net − U-Net), by seed">
        <table className="table">
          <thead>
            <tr>
              <th>Seed</th>
              {CLASS_KEYS.map((k) => (
                <th key={k}>
                  <span className="swatch sm" style={{ background: classColor(k) }} aria-hidden="true" />
                  {classLabel(k)}
                </th>
              ))}
              <th>macro</th>
              <th>framework verdict</th>
            </tr>
          </thead>
          <tbody>
            {REAL_M11.perSeedDeltaIoU.map((row) => (
              <tr key={row.seed}>
                <td>{row.seed}</td>
                {CLASS_KEYS.map((k) => {
                  const d = delta(row[k] as number);
                  return <td key={k} className={`mono delta-${d.cls}`}>{d.text}</td>;
                })}
                <td className={`mono delta-${delta(row.macro).cls}`}>{delta(row.macro).text}</td>
                <td><RegimeBadge regime={row.verdict === 'IMPROVED' ? 'REAL' : 'DEFERRED'} title={row.verdict} />{' '}{row.verdict}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card title="Honest reading">
        <ul className="bullets">
          <li><strong>Thin cloud (primary):</strong> {REAL_M11.thinCloud.recall}; false-negatives {REAL_M11.thinCloud.falseNegatives}. Improves in all 3 seeds.</li>
          <li><strong>Cloud shadow (trade-off):</strong> {REAL_M11.cloudShadow.note}.</li>
          <li>The per-seed framework verdict flips (IMPROVED / REGRESSION / REGRESSION); overall <strong>MIXED</strong> — no uniform winner, no forced conclusion.</li>
          <li>Compute cost: params ×{(REAL_M11.params.attention_unet / REAL_M11.params.unet).toFixed(3)}, training time {REAL_M11.trainTimeRatio}.</li>
          <li><RegimeBadge regime="NOT_YET_MEASURED" /> Formal AC-4 KPIs — this bounded run does not populate them.</li>
        </ul>
      </Card>
    </div>
  );
}

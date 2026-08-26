// Class-aware visual components — legend, per-class metric table, class-distribution bar.
// All reuse the M5 CloudSEN12 palette + names; colour is never the only signal (labels always shown).
import { CLOUDSEN12_CLASSES, PRIMARY_CLASS, TRADEOFF_CLASS, classColor, classLabel } from '../utils/colors';
import { fmtInt, fmtMetric } from '../utils/format';

export function ClassLegend() {
  return (
    <ul className="legend" aria-label="CloudSEN12 class legend">
      {CLOUDSEN12_CLASSES.map((c) => (
        <li key={c.name}>
          <span className="swatch" style={{ background: c.hex }} aria-hidden="true" />
          {c.label}
          {c.name === PRIMARY_CLASS && <em className="tag-primary"> primary</em>}
          {c.name === TRADEOFF_CLASS && <em className="tag-tradeoff"> trade-off</em>}
        </li>
      ))}
    </ul>
  );
}

// A per-class IoU table (undefined preserved). Rows follow the canonical class order.
export function PerClassTable({ perClass }: { perClass: Record<string, number | null> }) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th>Class</th>
          <th>IoU</th>
        </tr>
      </thead>
      <tbody>
        {CLOUDSEN12_CLASSES.map((c) => {
          const highlight =
            c.name === PRIMARY_CLASS ? 'row-primary' : c.name === TRADEOFF_CLASS ? 'row-tradeoff' : '';
          const has = Object.prototype.hasOwnProperty.call(perClass, c.name);
          return (
            <tr key={c.name} className={highlight}>
              <td>
                <span className="swatch sm" style={{ background: c.hex }} aria-hidden="true" />
                {c.label}
                {c.name === PRIMARY_CLASS && <em className="tag-primary"> · thin cloud</em>}
                {c.name === TRADEOFF_CLASS && <em className="tag-tradeoff"> · cloud shadow</em>}
              </td>
              <td className="mono">{has ? fmtMetric(perClass[c.name]) : 'undefined'}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

// Horizontal stacked bar of class pixel counts (from a real /predict response).
export function ClassDistributionBar({ counts }: { counts: Record<string, number> }) {
  const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
  // counts keys are class indices ("0".."3") from the backend.
  const segments = CLOUDSEN12_CLASSES.map((c) => ({
    ...c,
    value: counts[String(c.index)] ?? 0,
  })).filter((s) => s.value > 0);

  return (
    <div>
      <div className="dist-bar" role="img" aria-label="Class pixel distribution">
        {segments.map((s) => (
          <span
            key={s.name}
            className="dist-seg"
            style={{ width: `${(s.value / total) * 100}%`, background: s.hex }}
            title={`${s.label}: ${s.value} px (${((s.value / total) * 100).toFixed(1)}%)`}
          />
        ))}
      </div>
      <table className="table sm">
        <tbody>
          {segments.map((s) => (
            <tr key={s.name}>
              <td>
                <span className="swatch sm" style={{ background: s.hex }} aria-hidden="true" />
                {classLabel(s.name)}
              </td>
              <td className="mono">{fmtInt(s.value)} px</td>
              <td className="mono">{((s.value / total) * 100).toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export { classColor };

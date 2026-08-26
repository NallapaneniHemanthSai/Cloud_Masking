import { useState } from 'react';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { postEvaluate } from '../services/api';
import type { EvaluateRequest, EvaluateResponse } from '../services/types';
import { Card, ErrorState, MetricTile, RegimeBadge } from '../components/ui';
import { PerClassTable } from '../components/ClassViz';
import { fmtMetric } from '../utils/format';

export function Evaluate() {
  const [form, setForm] = useState<Partial<EvaluateRequest>>({
    mode: 'multiclass',
    dataset: 'cloudsen12',
    split: 'test',
    seed: 0,
    synthetic: true,
  });
  const { run, pending, error, result } = useAsyncAction<Partial<EvaluateRequest>, EvaluateResponse>(postEvaluate);
  const set = (k: keyof EvaluateRequest, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="page">
      <div className="page-head">
        <h1>Evaluation</h1>
        <p className="muted">
          Runs the M8 metric suite. The API exposes <RegimeBadge regime="SYNTHETIC" /> evaluation only —
          per-class IoU is surfaced (thin cloud &amp; cloud shadow highlighted); undefined values are shown
          as <code>undefined</code>, never 0.
        </p>
      </div>

      <div className="grid-2">
        <Card title="Configuration">
          <form className="form" onSubmit={(e) => { e.preventDefault(); void run(form); }}>
            <label>Mode
              <select value={form.mode} onChange={(e) => set('mode', e.target.value)}>
                <option value="multiclass">multiclass (CloudSEN12)</option>
                <option value="binary">binary (On Cloud N)</option>
              </select>
            </label>
            <label>Split
              <select value={form.split} onChange={(e) => set('split', e.target.value)}>
                <option value="test">test</option>
                <option value="val">val</option>
                <option value="train">train</option>
              </select>
            </label>
            <label>Seed
              <input type="number" value={form.seed} onChange={(e) => set('seed', Number(e.target.value))} />
            </label>
            <button className="btn primary" type="submit" disabled={pending}>
              {pending ? 'Evaluating…' : 'Run evaluation'}
            </button>
          </form>
        </Card>

        <Card title="Result">
          {error && <ErrorState error={error} />}
          {!error && !result && <p className="muted">Submit to run a synthetic evaluation.</p>}
          {result && (
            <div>
              <div className="result-head">
                <RegimeBadge regime={result.data_regime} />
                <span className="mono small">{result.evaluation_id}</span>
              </div>
              <div className="tiles">
                <MetricTile label="Macro IoU" value={fmtMetric(result.macro_iou)} />
                <MetricTile label="Thin-cloud IoU" value={fmtMetric(result.thin_cloud_iou)} hint="primary class" />
                <MetricTile label="Pixel accuracy" value={fmtMetric(result.pixel_accuracy)} />
              </div>
              <h3>Per-class IoU</h3>
              <PerClassTable perClass={result.per_class_iou} />
              <p className="muted small">{result.notes}</p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

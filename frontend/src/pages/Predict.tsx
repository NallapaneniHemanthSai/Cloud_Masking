import { useState } from 'react';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { postPredict } from '../services/api';
import type { PredictRequest, PredictResponse } from '../services/types';
import { Card, ErrorState, RegimeBadge } from '../components/ui';
import { ClassDistributionBar } from '../components/ClassViz';

const DEFAULTS: Partial<PredictRequest> = {
  architecture: 'unet',
  in_channels: 13,
  num_classes: 4,
  encoder_depth: 2,
  base_channels: 8,
  device: 'cpu',
  patch_size: 32,
  synthetic: true,
};

export function Predict() {
  const [form, setForm] = useState<Partial<PredictRequest>>(DEFAULTS);
  const { run, pending, error, result } = useAsyncAction<Partial<PredictRequest>, PredictResponse>(postPredict);

  const set = (k: keyof PredictRequest, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="page">
      <div className="page-head">
        <h1>Prediction</h1>
        <p className="muted">
          Runs tiled inference on the backend (M6 model + M4 tiling). A synthetic input is used by default —
          results are <RegimeBadge regime="SYNTHETIC" /> unless a trained checkpoint is supplied.
        </p>
      </div>

      <div className="grid-2">
        <Card title="Configuration">
          <form
            className="form"
            onSubmit={(e) => {
              e.preventDefault();
              void run(form);
            }}
          >
            <label>Architecture
              <select value={form.architecture} onChange={(e) => set('architecture', e.target.value)}>
                <option value="unet">unet (baseline)</option>
                <option value="attention_unet">attention_unet (improved)</option>
              </select>
            </label>
            <label>Device
              <select value={form.device} onChange={(e) => set('device', e.target.value)}>
                <option value="cpu">cpu</option>
                <option value="mps">mps</option>
                <option value="auto">auto</option>
              </select>
            </label>
            <label>Input channels
              <input type="number" value={form.in_channels} min={1} max={16} onChange={(e) => set('in_channels', Number(e.target.value))} />
            </label>
            <label>Classes
              <input type="number" value={form.num_classes} min={2} max={4} onChange={(e) => set('num_classes', Number(e.target.value))} />
            </label>
            <label>Encoder depth
              <input type="number" value={form.encoder_depth} min={1} max={4} onChange={(e) => set('encoder_depth', Number(e.target.value))} />
            </label>
            <label>Base channels
              <input type="number" value={form.base_channels} min={4} max={64} onChange={(e) => set('base_channels', Number(e.target.value))} />
            </label>
            <label>Patch size
              <input type="number" value={form.patch_size} min={8} max={256} step={8} onChange={(e) => set('patch_size', Number(e.target.value))} />
            </label>
            <button className="btn primary" type="submit" disabled={pending}>
              {pending ? 'Predicting…' : 'Run prediction'}
            </button>
          </form>
        </Card>

        <Card title="Result">
          {error && <ErrorState error={error} />}
          {!error && !result && <p className="muted">Submit the form to run a prediction.</p>}
          {result && (
            <div>
              <div className="result-head">
                <RegimeBadge regime={result.data_regime} />
                <span className="mono small">{result.prediction_id}</span>
              </div>
              <dl className="kv">
                <dt>architecture</dt><dd>{result.architecture}</dd>
                <dt>device</dt><dd>{result.device}</dd>
                <dt>input shape</dt><dd className="mono">[{result.input_shape.join(', ')}]</dd>
                <dt>output shape</dt><dd className="mono">[{result.output_shape.join(', ')}]</dd>
                <dt>source</dt><dd className="mono">{result.source || '—'}</dd>
              </dl>
              <h3>Predicted class distribution</h3>
              <ClassDistributionBar counts={result.class_pixel_counts} />
              <p className="muted small note-deferred">
                Full pixel-mask rendering is <RegimeBadge regime="DEFERRED" /> — the API returns class pixel
                counts, not mask pixels. No mask is fabricated. An untrained model produces a structural
                distribution, not a benchmark.
              </p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

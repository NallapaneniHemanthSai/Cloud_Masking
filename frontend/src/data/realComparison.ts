// REAL DATA — bounded first experiment. Values transcribed verbatim from the committed report:
//   docs/comparison/real_experiment_cloudsen12.md
// This is the single source; the UI must not invent, re-derive, or reinterpret these numbers, and must
// preserve the MIXED conclusion. NOT the frozen AC-4 benchmark. 32-sample CloudSEN12+ subset, 3 seeds, MPS.
export interface SeedDeltas {
  seed: number;
  clear: number;
  thick_cloud: number;
  thin_cloud: number;
  cloud_shadow: number;
  macro: number;
  verdict: string;
}

export const REAL_M11 = {
  dataset: 'CloudSEN12+ L1C 1.1.2 (bounded 32-sample subset)',
  device: 'mps',
  seeds: 3,
  params: { unet: 484228, attention_unet: 490005 },
  trainTimeRatio: '≈ ×1.2–1.3',
  conclusion: 'MIXED',
  perSeedDeltaIoU: [
    { seed: 1, clear: -0.024, thick_cloud: -0.057, thin_cloud: 0.047, cloud_shadow: -0.003, macro: -0.009, verdict: 'IMPROVED' },
    { seed: 2, clear: -0.014, thick_cloud: 0.028, thin_cloud: 0.076, cloud_shadow: -0.029, macro: 0.015, verdict: 'REGRESSION' },
    { seed: 3, clear: 0.039, thick_cloud: 0.122, thin_cloud: 0.028, cloud_shadow: -0.022, macro: 0.042, verdict: 'REGRESSION' },
  ] as SeedDeltas[],
  thinCloud: { meanDeltaIoU: 0.05, recall: '↑ every seed (e.g. 0.666→0.745)', falseNegatives: '↓ every seed (24k–52k fewer)' },
  cloudShadow: { note: 'consistently regressed slightly (hardest class, IoU ≈ 0.08–0.10 for both models)' },
  source: 'docs/comparison/real_experiment_cloudsen12.md',
};

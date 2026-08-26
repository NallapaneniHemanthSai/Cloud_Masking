// Small display helpers. Undefined metrics are shown as "undefined" (never 0) — mirroring the M8 rule.

export function fmtMetric(v: number | null | undefined, digits = 4): string {
  if (v === null || v === undefined) return 'undefined';
  return v.toFixed(digits);
}

export function fmtSeconds(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—';
  return `${v.toFixed(3)} s`;
}

export function fmtInt(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—';
  return v.toLocaleString();
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export function shortHash(h: string | null | undefined, n = 12): string {
  if (!h) return '—';
  return h.length > n ? h.slice(0, n) : h;
}

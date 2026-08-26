// CloudSEN12 class palette — reused VERBATIM from the backend M5 colormap
// (backend/app/visualization/colormap.py, DEFAULT_CLOUDSEN12_COLORMAP). Do not diverge.
export interface ClassColor {
  index: number;
  name: string;
  label: string;
  hex: string;
}

export const CLOUDSEN12_CLASSES: ClassColor[] = [
  { index: 0, name: 'clear', label: 'Clear', hex: '#1a9850' },
  { index: 1, name: 'thick_cloud', label: 'Thick cloud', hex: '#f7f7f7' },
  { index: 2, name: 'thin_cloud', label: 'Thin cloud', hex: '#fdae61' },
  { index: 3, name: 'cloud_shadow', label: 'Cloud shadow', hex: '#4d4d4d' },
];

const BY_NAME = new Map(CLOUDSEN12_CLASSES.map((c) => [c.name, c]));
const BY_INDEX = new Map(CLOUDSEN12_CLASSES.map((c) => [String(c.index), c]));

export function classColor(nameOrIndex: string): string {
  return (BY_NAME.get(nameOrIndex) ?? BY_INDEX.get(nameOrIndex))?.hex ?? '#888888';
}

export function classLabel(name: string): string {
  return BY_NAME.get(name)?.label ?? name;
}

// The two research-critical classes highlighted throughout the UI.
export const PRIMARY_CLASS = 'thin_cloud';
export const TRADEOFF_CLASS = 'cloud_shadow';

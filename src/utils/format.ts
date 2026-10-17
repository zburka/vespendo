const HONAPOK = [
  'január', 'február', 'március', 'április', 'május', 'június',
  'július', 'augusztus', 'szeptember', 'október', 'november', 'december',
];

export function formatFt(osszeg: number): string {
  return `${Math.round(osszeg).toLocaleString('hu-HU')} Ft`;
}

/** '2026-10' -> '2026. október' */
export function formatHonap(honap: string): string {
  const [ev, ho] = honap.split('-');
  return `${ev}. ${HONAPOK[Number(ho) - 1]}`;
}

/** '2026-12' + 1 -> '2027-01' */
export function leptetHonap(honap: string, delta: number): string {
  const [ev, ho] = honap.split('-').map(Number);
  const d = new Date(ev, ho - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

export function aktualisHonap(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

/** Spec: zöld < 75%, sárga 75–90%, piros > 90% */
export function keretSzin(szazalek: number): string {
  if (szazalek > 90) return '#d32f2f';
  if (szazalek >= 75) return '#f9a825';
  return '#2e7d32';
}

/** '2026-10-15' -> '2026. október 15.' */
export function formatNap(datum: string): string {
  const [ev, ho, nap] = datum.split('-').map(Number);
  return `${ev}. ${HONAPOK[ho - 1]} ${nap}.`;
}

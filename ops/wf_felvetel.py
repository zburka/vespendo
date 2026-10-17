"""POST /webhook/tranzakcio-felvetel: kézi tétel rögzítése (készpénzes kiadás, egyéb)."""
from n8nlib import *

BR = BASEROW + '/api/database/rows/table/'
ELO = r"""
const b = $('Webhook').first().json.body || {};
const osszeg = Number(b.osszeg);
if (!isFinite(osszeg) || osszeg <= 0) throw new Error('Az összeg legyen pozitív szám');
if (!/^\d{4}-\d{2}-\d{2}$/.test(String(b.datum || '')) || isNaN(Date.parse(b.datum))) throw new Error('Érvénytelen dátum (ÉÉÉÉ-HH-NN)');
const kat = String(b.kategoria_id || '');
if (!/^\d+$/.test(kat)) throw new Error('Érvénytelen kategória');
const kereskedo = String(b.kereskedo || '').trim();
if (!kereskedo) throw new Error('A megnevezés kötelező');
const tipus = ['kiadas', 'bevetel_egyszeri', 'bevetel_rendszeres'].includes(b.tipus) ? b.tipus : 'kiadas';
const tulajdonos = ['kozos', 'ferj', 'feleseg'].includes(b.tulajdonos) ? b.tulajdonos : 'kozos';
const mod = ['kartya', 'keszpenz', 'atutalas'].includes(b.fizetesi_mod) ? b.fizetesi_mod : 'keszpenz';
return [{ json: { sor: { kereskedo: kereskedo.slice(0, 200), datum: b.datum, osszeg, kategoria_id: [Number(kat)], tipus, tulajdonos,
  fizetesi_mod: mod, forras: 'kezi', allapot: 'lezart', megjegyzes: String(b.megjegyzes || '').slice(0, 1000) } } }];
"""
nodes = [
    webhook('Webhook', 'tranzakcio-felvetel', 'POST', (0, 0)),
    code('Előkészítés', ELO, (240, 0), hiba_ag=True),
    http('Rögzítés', 'POST', f"{BR}{T['tranzakciok']}/?user_field_names=true", (480, 0),
         body='={{ JSON.stringify($json.sor) }}', creds=cred_baserow(), hiba_ag=True),
    respond('Válasz', "={{ { status: 'success', id: String($json.id) } }}", (720, 0)),
    hiba_valasz((480, 240)),
]
k = {}
osszekot(k, 'Webhook', 'Előkészítés'); osszekot(k, 'Előkészítés', 'Rögzítés'); osszekot(k, 'Rögzítés', 'Válasz')
for n in ('Előkészítés', 'Rögzítés'): osszekot(k, n, 'Hiba válasz', 1)
telepit('VeSpendo – Kézi tétel felvétele', nodes, k)

"""POST /webhook/banki-fajl-gyors-import: egy hívásban elemez és importál (iOS Parancsok / megosztás menü)."""
from n8nlib import *

APPKULCS = {'httpHeaderAuth': {'id': CRED['VeSpendo App (X-App-Key)'], 'name': 'VeSpendo App (X-App-Key)'}}
PARSER = {'httpHeaderAuth': {'id': CRED['VeSpendo Parser (API key)'], 'name': 'VeSpendo Parser (API key)'}}

ELOKESZIT = HZ_JS + r"""
// JSON ({fajl_nev, fajl_base64, feltolto}) VAGY nyers fájl a kérés törzsében (iOS Parancsok: törzs = Fájl)
const w = $('Webhook').first();
const b = w.json.body || {};
const q = w.json.query || {};
let base64 = b.fajl_base64;
let nev = b.fajl_nev;
if (!base64 && w.binary && w.binary.data) {
  const buf = await this.helpers.getBinaryDataBuffer(0, 'data');
  base64 = buf.toString('base64');
  nev = nev || w.binary.data.fileName || q.nev || 'kivonat.pdf';
}
if (!base64) throw new Error('Hiányzik a fájl: küldd a fájlt a kérés törzsében, vagy JSON-ban fajl_base64 mezőként');
const feltolto = String(b.feltolto || q.feltolto || SZEMELY);
if (!/^[a-z0-9_]{1,30}$/.test(feltolto)) throw new Error('Érvénytelen feltolto (a személy kulcsa kell)');
return [{ json: { fajl_nev: String(nev || 'kivonat.pdf'), fajl_base64: String(base64), feltolto, hz: HZ } }];
"""
ATADAS = r"""
const e = $('Előkészítés').first().json;
const v = $input.first().json;
if (v.statusCode !== 200 || v.body?.status !== 'success') throw new Error(v.body?.uzenet || 'A fájl elemzése nem sikerült');
const d = v.body.data;
return [{ json: { hz: e.hz, feltolto: e.feltolto, tranzakciok: d.tranzakciok, megbizhatosag: d.megbizhatosag, figyelmeztetesek: d.figyelmeztetesek, tetelszam: d.tranzakciok.length } }];
"""
VALASZ = r"""
const a = $('Átadás').first().json;
const r = $input.first().json;
if (r.status !== 'success') throw new Error(r.uzenet || 'Az import nem sikerült');
const o = r.data;
const uzenet = `${o.uj} új tétel` + (o.duplikalt ? `, ${o.duplikalt} már rögzítve volt` : '') + (o.egyeztetve ? `, ${o.egyeztetve} nyugtával párosítva` : '') +
  (a.megbizhatosag !== 'magas' ? ` (a felismerés megbízhatósága: ${a.megbizhatosag})` : '');
return [{ json: { status: 'success', uzenet, tetelszam: a.tetelszam, megbizhatosag: a.megbizhatosag, figyelmeztetesek: a.figyelmeztetesek, osszegzes: o } }];
"""
nodes = [
    webhook('Webhook', 'banki-fajl-gyors-import', 'POST', (0, 0)),
    code('Előkészítés', ELOKESZIT, (240, 0), hiba_ag=True),
    http('Python elemző', 'POST', 'http://vespendo-parser:8000/parse', (480, 0),
         body='={{ JSON.stringify({ fajl_nev: $json.fajl_nev, fajl_base64: $json.fajl_base64 }) }}', creds=PARSER, teljes=True),
    code('Átadás', ATADAS, (720, 0), hiba_ag=True),
    http('Import', 'POST', f'http://localhost:5678/webhook/{UT_ELOTAG}banki-import', (960, 0),
         body='={{ JSON.stringify({ feltolto: $json.feltolto, tranzakciok: $json.tranzakciok }) }}', creds=APPKULCS, never_error=True,
         fejlec={'X-Haztartas': '={{ $json.hz }}', 'X-Szemely': '={{ $json.feltolto }}'}),
    code('Válasz összeállítása', VALASZ, (1200, 0), hiba_ag=True),
    respond('Válasz', '={{ $json }}', (1440, 0)),
    hiba_valasz((720, 240)),
]
k = {}
for a, b in [('Webhook', 'Előkészítés'), ('Előkészítés', 'Python elemző'), ('Python elemző', 'Átadás'), ('Átadás', 'Import'),
             ('Import', 'Válasz összeállítása'), ('Válasz összeállítása', 'Válasz')]: osszekot(k, a, b)
for n in ('Előkészítés', 'Átadás', 'Válasz összeállítása'): osszekot(k, n, 'Hiba válasz', 1)
telepit('VeSpendo – Banki fájl gyors import', nodes, k)

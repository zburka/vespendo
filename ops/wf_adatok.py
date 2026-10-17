from n8nlib import *

BR = BASEROW + '/api/database/rows/table/'
def lista(nev, tabla, poz, kiegeszites=''):
    return http(nev, 'GET', f"{BR}{T[tabla]}/?user_field_names=true&size=200{kiegeszites}", poz, creds=cred_baserow(), lapozas=True)

# ---------- GET /webhook/adatok : kategóriák, keretek, előfizetések, célok, szabályok
ADATOK = r"""
const sorok = (nev) => $(nev).all().flatMap(i => i.json.results || []);
const link = (v) => (v && v[0]) ? String(v[0].id) : '';
const szam = (v) => v === null || v === undefined || v === '' ? 0 : Number(v);
return [{ json: {
  kategoriak: sorok('Kategóriák').map(r => ({ id: String(r.id), nev: r.nev, tipus: r.tipus?.value, ikon: r.ikon || '' })),
  keretek: sorok('Keretek').map(r => ({ id: String(r.id), kategoria_id: link(r.kategoria_id), havi_keret: szam(r.havi_keret), aktiv: !!r.aktiv })),
  elofizetesek: sorok('Előfizetések').map(r => ({ id: String(r.id), megnevezes: r.megnevezes, varhato_osszeg: szam(r.varhato_osszeg), esedekesseg_napja: szam(r.esedekesseg_napja), kategoria_id: link(r.kategoria_id) })),
  celok: sorok('Célok').map(r => ({ id: String(r.id), cel_neve: r.cel_neve, celosszeg: szam(r.celosszeg), aktualis_osszeg: szam(r.aktualis_osszeg) })),
  szabalyok: sorok('Szabályok').map(r => ({ id: String(r.id), minta: r.minta, kategoria_id: link(r.kategoria_id), alapertelmezett_tulajdonos: r.alapertelmezett_tulajdonos?.value })),
} }];
"""
nodes = [
    webhook('Webhook', 'adatok', 'GET', (0, 0)),
    lista('Kategóriák', 'kategoriak', (240, 0)),
    lista('Keretek', 'koltsegkeretek', (480, 0)),
    lista('Előfizetések', 'elofizetesek', (720, 0)),
    lista('Célok', 'megtakaritasi_celok', (960, 0)),
    lista('Szabályok', 'szabalymotor', (1200, 0)),
    code('Összeállítás', ADATOK, (1440, 0)),
    respond('Válasz', '={{ $json }}', (1680, 0)),
]
k = {}
lanc = ['Webhook', 'Kategóriák', 'Keretek', 'Előfizetések', 'Célok', 'Szabályok', 'Összeállítás', 'Válasz']
for a, b in zip(lanc, lanc[1:]): osszekot(k, a, b)
telepit('VeSpendo – Alapadatok', nodes, k)

# ---------- GET /webhook/tranzakciok?honap=YYYY-MM
TRANZ = r"""
const link = (v) => (v && v[0]) ? String(v[0].id) : '';
const sorok = $input.all().flatMap(i => i.json.results || []);
return [{ json: { tranzakciok: sorok.map(r => ({
  id: String(r.id), datum: r.datum, osszeg: Number(r.osszeg), kereskedo: r.kereskedo, kategoria_id: link(r.kategoria_id),
  tipus: r.tipus?.value, tulajdonos: r.tulajdonos?.value, fizetesi_mod: r.fizetesi_mod?.value, forras: r.forras?.value,
  allapot: r.allapot?.value, megjegyzes: r.megjegyzes || undefined, nyugta_kep_url: r.nyugta_kep_url || undefined,
})) } }];
"""
url = (f"{BR}{T['tranzakciok']}/?user_field_names=true&size=200"
       "{{ /^\\d{4}-\\d{2}$/.test($json.query.honap || '') ? '&filter__datum__contains=' + $json.query.honap : '' }}")
nodes = [
    webhook('Webhook', 'tranzakciok', 'GET', (0, 0)),
    http('Tranzakciók', 'GET', '=' + url, (260, 0), creds=cred_baserow(), lapozas=True),
    code('Összeállítás', TRANZ, (520, 0)),
    respond('Válasz', '={{ $json }}', (780, 0)),
]
k = {}
for a, b in [('Webhook', 'Tranzakciók'), ('Tranzakciók', 'Összeállítás'), ('Összeállítás', 'Válasz')]: osszekot(k, a, b)
telepit('VeSpendo – Tranzakciók', nodes, k)

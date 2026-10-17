from n8nlib import *

BR = BASEROW + '/api/database/rows/table/'
HONAP = "{{ /^\\d{4}-\\d{2}$/.test($('Webhook').first().json.query.honap || '') ? $('Webhook').first().json.query.honap : $now.format('yyyy-MM') }}"

SZAMOL = r"""
const honap = (/^\d{4}-\d{2}$/.test($('Webhook').first().json.query.honap || '')) ? $('Webhook').first().json.query.honap : new Date().toISOString().slice(0, 7);
const sorok = (nev) => $(nev).all().flatMap(i => i.json.results || []);
const katId = (v) => (v && v[0]) ? v[0].id : null;
const tr = sorok('Tranzakciók').map(r => ({ osszeg: Number(r.osszeg), kereskedo: String(r.kereskedo || ''), kat: katId(r.kategoria_id), tipus: r.tipus?.value, tul: r.tulajdonos?.value }));
const kategoriak = Object.fromEntries(sorok('Kategóriák').map(r => [r.id, r.nev]));
const kiadasok = tr.filter(t => t.tipus === 'kiadas');
const sum = (l) => l.reduce((s, t) => s + t.osszeg, 0);
const osszes_bevetel = sum(tr.filter(t => t.tipus !== 'kiadas'));
const osszes_kiadas = sum(kiadasok);
const keretek = sorok('Keretek').filter(r => r.aktiv).map(r => {
  const keret = Number(r.havi_keret) || 0;
  const elkoltve = sum(kiadasok.filter(t => t.kat === katId(r.kategoria_id)));
  return { kategoria: kategoriak[katId(r.kategoria_id)] || '?', havi_keret: keret, elkoltve, szazalek: keret ? Math.round(elkoltve / keret * 100) : 0 };
});
const elofizetesek = sorok('Előfizetések').map(r => {
  const nev = String(r.megnevezes || '').split(' ')[0].toLowerCase();
  return { id: String(r.id), megnevezes: r.megnevezes, varhato_osszeg: Number(r.varhato_osszeg) || 0, esedekesseg_napja: Number(r.esedekesseg_napja) || 0,
           kategoria_id: String(katId(r.kategoria_id) ?? ''), kifizetve: !!nev && kiadasok.some(t => t.kereskedo.toLowerCase().includes(nev)) };
});
return [{ json: {
  osszes_bevetel, osszes_kiadas, egyenleg: osszes_bevetel - osszes_kiadas,
  bontas_tulajdonos_szerint: { kozos: sum(kiadasok.filter(t => t.tul === 'kozos')), ferj_sajat: sum(kiadasok.filter(t => t.tul === 'ferj')), feleseg_sajat: sum(kiadasok.filter(t => t.tul === 'feleseg')) },
  keretek, elofizetesek,
  varhato_hatralevo_elofizetesek: elofizetesek.filter(e => !e.kifizetve).reduce((s, e) => s + e.varhato_osszeg, 0),
  ai_elemzes: '',
} }];
"""
def lista(nev, tabla, poz, plusz=''):
    return http(nev, 'GET', f"{BR}{T[tabla]}/?user_field_names=true&size=200{plusz}", poz, creds=cred_baserow(), lapozas=True)

nodes = [
    webhook('Webhook', 'havi-osszesito', 'GET', (0, 0)),
    http('Tranzakciók', 'GET', f"={BR}{T['tranzakciok']}/?user_field_names=true&size=200&filter__datum__contains=" + HONAP, (260, 0),
         creds=cred_baserow(), lapozas=True),
    lista('Keretek', 'koltsegkeretek', (520, 0)),
    lista('Előfizetések', 'elofizetesek', (780, 0)),
    lista('Kategóriák', 'kategoriak', (1040, 0)),
    code('Számítás', SZAMOL, (1300, 0)),
    respond('Válasz', '={{ $json }}', (1560, 0)),
]
k = {}
lanc = ['Webhook', 'Tranzakciók', 'Keretek', 'Előfizetések', 'Kategóriák', 'Számítás', 'Válasz']
for a, b in zip(lanc, lanc[1:]): osszekot(k, a, b)
telepit('VeSpendo – Havi összesítő', nodes, k)

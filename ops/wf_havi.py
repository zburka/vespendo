from n8nlib import *

HONAP = "{{ /^\\d{4}-\\d{2}$/.test($('Webhook').first().json.query.honap || '') ? $('Webhook').first().json.query.honap : $now.format('yyyy-MM') }}"

SZAMOL = HZ_JS + r"""
const honap = (/^\d{4}-\d{2}$/.test($('Webhook').first().json.query.honap || '')) ? $('Webhook').first().json.query.honap : new Date().toISOString().slice(0, 7);
const sorok = (nev) => $(nev).all().flatMap(i => i.json.results || []);
const katId = (v) => (v && v[0]) ? v[0].id : null;
const trMind = sorok('Tranzakciók').map(r => ({ osszeg: Number(r.osszeg), kereskedo: String(r.kereskedo || ''), kat: katId(r.kategoria_id), tipus: r.tipus?.value, tul: r.tulajdonos || 'kozos' }));
const kategoriak = Object.fromEntries(sorok('Kategóriák').map(r => [r.id, r.nev]));
const katTipus = Object.fromEntries(sorok('Kategóriák').map(r => [r.id, r.tipus?.value]));
// a belső átvezetés (se kiadás, se bevétel) kimarad az összesítésekből
const tr = trMind.filter(t => katTipus[t.kat] !== 'atvezetes');
const kiadasok = tr.filter(t => t.tipus === 'kiadas');
const katNevek = {};
for (const t of kiadasok) { const n = kategoriak[t.kat] || 'Egyéb'; katNevek[n] = (katNevek[n] || 0) + t.osszeg; }
const top = Object.entries(katNevek).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([nev, osszeg]) => ({ nev, osszeg: Math.round(osszeg) }));
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
const cel = sorok('Célok').map(r => ({ nev: r.cel_neve, cel: Number(r.celosszeg) || 0, jelenleg: Number(r.aktualis_osszeg) || 0 }));
const adat = { honap, bevetel: Math.round(osszes_bevetel), kiadas: Math.round(osszes_kiadas), egyenleg: Math.round(osszes_bevetel - osszes_kiadas), legnagyobb_kiadasok: top,
  keretek: keretek.map(k => ({ kategoria: k.kategoria, keret: k.havi_keret, elkoltve: Math.round(k.elkoltve), szazalek: k.szazalek })), megtakaritasi_celok: cel };
const lenyomat = JSON.stringify(adat);
const statik = $getWorkflowStaticData('global');
statik.ai = statik.ai || {};
const aikulcs = HZ + '|' + honap;
const tarolt = statik.ai[aikulcs];
const friss = !!tarolt && tarolt.l === lenyomat;
return [{ json: {
  kell_ai: tr.length > 0 && !friss, lenyomat, ai_adat: adat, honap, aikulcs,
  osszes_bevetel, osszes_kiadas, egyenleg: osszes_bevetel - osszes_kiadas,
  bontas_szemely_szerint: kiadasok.reduce((m, t) => { m[t.tul] = (m[t.tul] || 0) + t.osszeg; return m; }, {}),
  bontas_tulajdonos_szerint: { kozos: sum(kiadasok.filter(t => t.tul === 'kozos')), ferj_sajat: 0, feleseg_sajat: 0 },
  keretek, elofizetesek,
  varhato_hatralevo_elofizetesek: elofizetesek.filter(e => !e.kifizetve).reduce((s, e) => s + e.varhato_osszeg, 0),
  ai_elemzes: friss ? tarolt.t : '',
} }];
"""
SONNET_BODY = ("={{ JSON.stringify({ model: 'claude-sonnet-5-5', max_tokens: 400, thinking: { type: 'between_tools' }, "
  "system: 'Családi pénzügyi tanácsadó vagy. A kapott havi adatok alapján írj 3-4 mondatos, barátságos, konkrét magyar nyelvű elemzést: "
  "mi alakult jól, mire figyeljenek (különösen a költségkeretek közelében), és adj egy gyakorlati tanácsot. Ne ismételd fel az összes számot, "
  "ne használj felsorolást vagy címsort. Csak a szöveget add vissza.', "
  "messages: [{ role: 'user', content: JSON.stringify($json.ai_adat) }] }) }}")

MENTES = r"""
const e = $('Számítás').first().json;
const szoveg = (($input.first().json.content || []).find(b => b.type === 'text') || {}).text;
const ai = (szoveg || '').trim();
if (ai) { const statik = $getWorkflowStaticData('global'); statik.ai = statik.ai || {}; statik.ai[e.aikulcs] = { l: e.lenyomat, t: ai }; }
return [{ json: { ...e, ai_elemzes: ai || e.ai_elemzes } }];
"""
def lista(nev, tabla, poz, plusz=''):
    return http(nev, 'GET', f"={BR}{T[tabla]}/?user_field_names=true&size=200{HZ_SZURO}{plusz}", poz, creds=cred_baserow(), lapozas=True)

nodes = [
    webhook('Webhook', 'havi-osszesito', 'GET', (0, 0)),
    http('Tranzakciók', 'GET', f"={BR}{T['tranzakciok']}/?user_field_names=true&size=200{HZ_SZURO}&filter__datum__contains=" + HONAP, (260, 0),
         creds=cred_baserow(), lapozas=True),
    lista('Keretek', 'koltsegkeretek', (520, 0)),
    lista('Előfizetések', 'elofizetesek', (780, 0)),
    lista('Kategóriák', 'kategoriak', (1040, 0)),
    lista('Célok', 'megtakaritasi_celok', (1300, 0)),
    code('Számítás', SZAMOL, (1560, 0)),
    if_('Kell AI elemzés?', '={{ $json.kell_ai }}', '', {'type': 'boolean', 'operation': 'true', 'singleValue': True}, (1800, 0)),
    http('Sonnet elemzés', 'POST', 'https://api.anthropic.com/v1/messages', (2040, -120), body=SONNET_BODY,
         creds={'httpHeaderAuth': {'id': CRED['VeSpendo Anthropic (x-api-key)'], 'name': 'VeSpendo Anthropic (x-api-key)'}},
         fejlec={'anthropic-version': '2023-06-01'}, never_error=True, retry=True),
    code('Mentés', MENTES, (2280, -120)),
    respond('Válasz', "={{ (() => { const { kell_ai, lenyomat, ai_adat, honap, aikulcs, ...x } = $json; return x; })() }}", (2520, 0)),
]
k = {}
lanc = ['Webhook', 'Tranzakciók', 'Keretek', 'Előfizetések', 'Kategóriák', 'Célok', 'Számítás', 'Kell AI elemzés?']
for a, b in zip(lanc, lanc[1:]): osszekot(k, a, b)
osszekot(k, 'Kell AI elemzés?', 'Sonnet elemzés', 0); osszekot(k, 'Kell AI elemzés?', 'Válasz', 1)
osszekot(k, 'Sonnet elemzés', 'Mentés'); osszekot(k, 'Mentés', 'Válasz')
telepit('VeSpendo – Havi összesítő', nodes, k)

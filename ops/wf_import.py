from n8nlib import *

BR = BASEROW + '/api/database/rows/table/'
KAT_ID = IDS['kategoriak']

# A Haiku besorolás csak akkor épül be, ha van a VeSpendo-nak saját Anthropic hitelesítője az n8n-ben.
HAIKU_NEV = 'VeSpendo Anthropic (x-api-key)'
HAIKU = HAIKU_NEV in CRED
ANTHROPIC = {'httpHeaderAuth': {'id': CRED.get(HAIKU_NEV), 'name': HAIKU_NEV}}

FELDOLGOZAS = r"""
const body = $('Webhook').first().json.body || {};
if (!Array.isArray(body.tranzakciok)) throw new Error('Hiányzó tranzakciok lista');
const feltolto = body.feltolto === 'feleseg' ? 'feleseg' : 'ferj';
const EGYEB = %(egyeb)d, FIZETES = %(fizetes)d;

const szabalyok = $('Szabályok').all().flatMap(i => i.json.results || [])
  .map(r => ({ minta: String(r.minta || '').toLowerCase(), kat: r.kategoria_id?.[0]?.id, tul: r.alapertelmezett_tulajdonos?.value }))
  .filter(r => r.minta && r.kat)
  .sort((a, b) => b.minta.length - a.minta.length);
const meglevo = $('Meglévő tranzakciók').all().flatMap(i => i.json.results || []);
const kulcsok = new Set(meglevo.map(r => r.import_kulcs).filter(Boolean));
const varakozo = meglevo.filter(r => r.allapot?.value === 'banki_egyeztetesre_var')
  .map(r => ({ id: r.id, datum: r.datum, osszeg: Number(r.osszeg), hasznalt: false }));

const uj = [], patch = [], ismeretlenek = [];
const o = { uj: 0, egyeztetve: 0, szaballyal: 0, ismeretlen: 0, duplikalt: 0 };
const szamlalo = {};
for (const t of body.tranzakciok) {
  const osszeg = Math.abs(Number(t.osszeg));
  if (!t.datum || !isFinite(osszeg) || osszeg === 0) continue;
  const nyers = String(t.kereskedo_nyers || '');
  const koz = String(t.kozlemeny || '');
  const alap = `${t.datum}|${osszeg}|${nyers}`;
  szamlalo[alap] = (szamlalo[alap] || 0) + 1;
  const kulcs = `${alap}#${szamlalo[alap]}`;
  if (kulcsok.has(kulcs)) { o.duplikalt++; continue; }
  const kiadas = t.irany !== 'bevetel';

  // 2. nyugtával párosítás: azonos összeg, a nyugta napja és +3 nap között
  if (kiadas) {
    const v = varakozo.find(v => !v.hasznalt && Math.abs(v.osszeg - osszeg) < 0.01 &&
      (Date.parse(t.datum) - Date.parse(v.datum)) / 864e5 >= 0 && (Date.parse(t.datum) - Date.parse(v.datum)) / 864e5 <= 3);
    if (v) { v.hasznalt = true; patch.push({ id: v.id, allapot: 'lezart', import_kulcs: kulcs }); o.egyeztetve++; continue; }
  }

  // 1. szabálymotor (0 token)
  const szoveg = (nyers + ' ' + koz).toLowerCase();
  const sz = szabalyok.find(r => szoveg.includes(r.minta));
  const sor = {
    kereskedo: (nyers || koz || 'Ismeretlen').slice(0, 200), datum: t.datum, osszeg,
    kategoria_id: [sz?.kat || (kiadas ? EGYEB : FIZETES)], tipus: kiadas ? 'kiadas' : 'bevetel_egyszeri', tulajdonos: sz?.tul || feltolto,
    fizetesi_mod: /k[aá]rty/i.test(koz + ' ' + nyers) ? 'kartya' : 'atutalas', forras: 'bank_import', allapot: 'lezart',
    megjegyzes: koz.slice(0, 1000), import_kulcs: kulcs,
  };
  if (sz) o.szaballyal++;
  else if (kiadas) ismeretlenek.push({ idx: uj.length, szoveg: (nyers + ' ' + koz).slice(0, 140), osszeg });
  uj.push(sor);
}
o.uj = uj.length;
o.ismeretlen = ismeretlenek.length;
return [{ json: { uj, patch, ismeretlenek, osszegzes: o, volt_ismeretlen: ismeretlenek.length > 0 } }];
""" % {'egyeb': KAT_ID['Egyéb'], 'fizetes': KAT_ID['Egyéb bevétel']}

CHUNKOK = r"""
const lista = $('Feldolgozás').first().json.ismeretlenek;
const out = [];
for (let i = 0; i < lista.length; i += 25) out.push({ json: { chunk: lista.slice(i, i + 25) } });
return out;
"""

from prompts import BESOROLAS_SYSTEM
HAIKU_BODY = ("={{ JSON.stringify({ model: 'claude-haiku-5-5', max_tokens: 700, thinking: { type: 'disabled' }, system: "
  + json.dumps(BESOROLAS_SYSTEM, ensure_ascii=False) + ", "
  "messages: [{ role: 'user', content: $json.chunk.map((c, i) => i + '|' + c.szoveg + '|' + c.osszeg).join('\\n') }] }) }}")

OSSZEFESULES = r"""
const alap = $('Feldolgozás').first().json;
const uj = alap.uj;
const KAT = %(kat)s;
const GEN = /^(vásárlás kártyával|áruvisszavét ellenértéke|azonnali fizetés.*|napközbeni átutalás.*|tranzakció.*)$/i;
const kulcs = (sz) => {
  for (let r of String(sz).split(', ').map(x => x.trim()).filter(Boolean)) {
    if (GEN.test(r) || /^[\d\W]+$/.test(r) || /\d+[,.]?\d*\s?EUR|\bEUR\b/i.test(r)) continue;
    r = r.replace(/\s*-?apple\b.*$/i, '').replace(/\s+\d{3,}.*$/, '').replace(/\*+/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
    if (r.length >= 4) return r;
  }
  return null;
};
let hasznalt = 0;
const tanult = {};
if (alap.volt_ismeretlen && %(haiku)s) {
  let haiku = [];
  try { haiku = $('Haiku besorolás').all(); } catch (e) { haiku = []; }
  const chunkok = $('Chunkok').all().map(i => i.json.chunk);
  const mintak = $('Szabályok').all().flatMap(i => i.json.results || []).map(r => String(r.minta || '').toLowerCase());
  chunkok.forEach((chunk, ci) => {
    let valasz = null;
    try {
      const szoveg = (haiku[ci]?.json?.content || []).find(b => b.type === 'text')?.text || '';
      valasz = JSON.parse(szoveg.replace(/```json|```/g, '').trim());
    } catch (e) { valasz = null; }
    // csak teljes, sorszám-kulcsos válasz érvényes: egy hiányos válasz nem csúsztathat el besorolást
    if (!valasz || typeof valasz !== 'object' || chunk.some((c, i) => !(String(i) in valasz))) return;
    chunk.forEach((c, i) => {
      const nev = valasz[String(i)];
      const id = KAT[nev];
      if (!id || nev === 'Egyéb') return;
      uj[c.idx].kategoria_id = [id];
      hasznalt++;
      const k = kulcs(uj[c.idx].kereskedo);
      if (k && !mintak.some(m => m.includes(k) || k.includes(m)) && !(k in tanult)) tanult[k] = id;
    });
  });
}
const darabok = [];
for (let i = 0; i < uj.length; i += 200) darabok.push(uj.slice(i, i + 200));
return [{ json: { uj_darabok: darabok, ai_besorolt: hasznalt, tanult } }];
""" % {'kat': json.dumps(KAT_ID, ensure_ascii=False), 'haiku': 'true' if HAIKU else 'false'}

LETREHOZAS_ITEMEK = r"""
const d = $('Összefésülés').first().json.uj_darabok;
return d.length ? d.map(x => ({ json: { items: x } })) : [{ json: { items: [] } }];
"""
PATCH_ITEMEK = r"""
const p = $('Feldolgozás').first().json.patch;
const out = [];
for (let i = 0; i < p.length; i += 200) out.push({ json: { items: p.slice(i, i + 200) } });
return out.length ? out : [{ json: { items: [] } }];
"""
TANULT_ITEMEK = r"""
const t = $('Összefésülés').first().json.tanult || {};
const items = Object.entries(t).map(([minta, kat]) => ({ minta, kategoria_id: [kat], alapertelmezett_tulajdonos: 'kozos' }));
return [{ json: { items } }];
"""
VALASZ = r"""
const alap = $('Feldolgozás').first().json;
const osz = { ...alap.osszegzes, ai_besorolt: $('Összefésülés').first().json.ai_besorolt, tanult_szabaly: Object.keys($('Összefésülés').first().json.tanult || {}).length };
const hibas = (nev) => { try { for (const i of $(nev).all()) if (!Array.isArray(i.json.items)) return true; } catch (e) {} return false; };
if (alap.uj.length && hibas('Új sorok írása')) throw new Error('A Baserow írás sikertelen (új sorok)');
if (alap.patch.length && hibas('Nyugták lezárása')) throw new Error('A Baserow írás sikertelen (nyugták)');
return [{ json: { status: 'success', data: osz } }];
"""

IGAZ = {'type': 'boolean', 'operation': 'true', 'singleValue': True}
NAGYOBB = {'type': 'number', 'operation': 'gt'}

nodes = [
    webhook('Webhook', 'banki-import', 'POST', (0, 0)),
    http('Szabályok', 'GET', f"{BR}{T['szabalymotor']}/?user_field_names=true&size=200", (240, 0), creds=cred_baserow(), lapozas=True),
    http('Meglévő tranzakciók', 'GET',
         f"{BR}{T['tranzakciok']}/?user_field_names=true&size=200&include=datum,osszeg,allapot,import_kulcs", (480, 0),
         creds=cred_baserow(), lapozas=True),
    code('Feldolgozás', FELDOLGOZAS, (720, 0), hiba_ag=True),
]
if HAIKU:
    nodes += [
        if_('Van ismeretlen?', '={{ $json.volt_ismeretlen }}', '', IGAZ, (960, 0)),
        code('Chunkok', CHUNKOK, (1200, -120)),
        http('Haiku besorolás', 'POST', 'https://api.anthropic.com/v1/messages', (1440, -120), body=HAIKU_BODY,
             creds=ANTHROPIC, fejlec={'anthropic-version': '2023-06-01'}, never_error=True, retry=True),
    ]
nodes += [
    code('Összefésülés', OSSZEFESULES, (1680, 0)),
    code('Létrehozás tételei', LETREHOZAS_ITEMEK, (1920, 0)),
    if_('Van új sor?', '={{ $json.items.length }}', 0, NAGYOBB, (2160, 0)),
    http('Új sorok írása', 'POST', f"{BR}{T['tranzakciok']}/batch/?user_field_names=true", (2400, -120),
         body='={{ JSON.stringify({ items: $json.items }) }}', creds=cred_baserow(), never_error=True),
    code('Patch tételei', PATCH_ITEMEK, (2640, 0)),
    if_('Van patch?', '={{ $json.items.length }}', 0, NAGYOBB, (2880, 0)),
    http('Nyugták lezárása', 'PATCH', f"{BR}{T['tranzakciok']}/batch/?user_field_names=true", (3120, -120),
         body='={{ JSON.stringify({ items: $json.items }) }}', creds=cred_baserow(), never_error=True),
    code('Tanult szabályok', TANULT_ITEMEK, (3360, 0)),
    if_('Van tanult szabály?', '={{ $json.items.length }}', 0, NAGYOBB, (3600, 0)),
    http('Szabályok mentése', 'POST', f"{BR}{T['szabalymotor']}/batch/?user_field_names=true", (3840, -120),
         body='={{ JSON.stringify({ items: $json.items }) }}', creds=cred_baserow(), never_error=True),
    code('Válasz összeállítása', VALASZ, (4080, 0), hiba_ag=True),
    respond('Válasz', '={{ $json }}', (4320, 0)),
    hiba_valasz((4080, 240)),
]
k = {}
osszekot(k, 'Webhook', 'Szabályok'); osszekot(k, 'Szabályok', 'Meglévő tranzakciók'); osszekot(k, 'Meglévő tranzakciók', 'Feldolgozás')
if HAIKU:
    osszekot(k, 'Feldolgozás', 'Van ismeretlen?')
    osszekot(k, 'Van ismeretlen?', 'Chunkok', 0); osszekot(k, 'Van ismeretlen?', 'Összefésülés', 1)
    osszekot(k, 'Chunkok', 'Haiku besorolás'); osszekot(k, 'Haiku besorolás', 'Összefésülés')
else:
    osszekot(k, 'Feldolgozás', 'Összefésülés')
osszekot(k, 'Összefésülés', 'Létrehozás tételei'); osszekot(k, 'Létrehozás tételei', 'Van új sor?')
osszekot(k, 'Van új sor?', 'Új sorok írása', 0); osszekot(k, 'Van új sor?', 'Patch tételei', 1)
osszekot(k, 'Új sorok írása', 'Patch tételei')
osszekot(k, 'Patch tételei', 'Van patch?')
osszekot(k, 'Van patch?', 'Nyugták lezárása', 0); osszekot(k, 'Van patch?', 'Tanult szabályok', 1)
osszekot(k, 'Nyugták lezárása', 'Tanult szabályok'); osszekot(k, 'Tanult szabályok', 'Van tanult szabály?')
osszekot(k, 'Van tanult szabály?', 'Szabályok mentése', 0); osszekot(k, 'Van tanult szabály?', 'Válasz összeállítása', 1)
osszekot(k, 'Szabályok mentése', 'Válasz összeállítása'); osszekot(k, 'Válasz összeállítása', 'Válasz')
osszekot(k, 'Feldolgozás', 'Hiba válasz', 1); osszekot(k, 'Válasz összeállítása', 'Hiba válasz', 1)
telepit('VeSpendo – Banki import', nodes, k)

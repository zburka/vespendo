from n8nlib import *

HAIKU_NEV = 'VeSpendo Anthropic (x-api-key)'
HAIKU = HAIKU_NEV in CRED

if not HAIKU:
    nodes = [
        webhook('Webhook', 'nyugta-feltoltes', 'POST', (0, 0)),
        respond('Nincs AI', "={{ { status: 'error', uzenet: 'A nyugtaolvasás még nincs beállítva (hiányzik az AI hitelesítő).' } }}", (260, 0), kod='503'),
    ]
    k = {}; osszekot(k, 'Webhook', 'Nincs AI')
    telepit('VeSpendo – Nyugta feltöltés', nodes, k)
    raise SystemExit(0)

ELOKESZIT = HZ_JS + r"""
const b = $('Webhook').first().json.body || {};
const m = /^data:(image\/(?:jpeg|png|webp|gif));base64,(.+)$/s.exec(String(b.kep_base64 || ''));
if (!m) throw new Error('Hiányzó vagy érvénytelen kep_base64');
const feltolto = String(b.feltolto || SZEMELY);
if (!/^[a-z0-9_]{1,30}$/.test(feltolto)) throw new Error('Érvénytelen feltolto (a személy kulcsa kell)');
const megj = String(b.megjegyzes || '').slice(0, 500);
const ma = new Date().toISOString().slice(0, 10);
const prompt = 'Magyar pénztári nyugta. A mai dátum: ' + ma + '. Add vissza KIZÁRÓLAG egy JSON objektumként: ' +
  '{"kereskedo": szöveg, "osszeg": a fizetendő végösszeg Ft-ban (szám), "datum": "YYYY-MM-DD" vagy null, ' +
  '"datumok": a nyugtán nyomtatott ÖSSZES dátum szövege pontosan úgy, ahogy írva van (pl. ["26/10/17", "2026.10.17."]), "fizetesi_mod": "kartya"|"keszpenz"|"atutalas", ' +
  '"bontott_tetelek": [{"kategoria": __KAT__, "osszeg": szám}]}. ' +
  (megj ? 'A felhasználó megjegyzése a tételbontásról (ezt használd a bontáshoz, az összegek összege a végösszeg): "' + megj + '". ' : 'A bontást a nyugta tételei alapján add meg: ha nem élelmiszer jellegű tételek is vannak (elektronika, ruházat, háztartási cikk), azokat külön kategóriába sorold. ');
return [{ json: { hz: HZ, feltolto, megj, anthropic_body: { model: 'claude-haiku-5-5', max_tokens: 500, thinking: { type: 'disabled' }, messages: [{ role: 'user', content: [
  { type: 'image', source: { type: 'base64', media_type: m[1], data: m[2] } }, { type: 'text', text: prompt }] }] } } }];
"""
KERES = r"""
// a háztartás saját kiadás-kategóriái kerülnek az utasításba (átnevezett / új kategóriák is)
const e = $('Előkészítés').first().json;
const nevek = $('Kategóriák').all().flatMap(i => i.json.results || []).filter(r => r.tipus?.value === 'kiadas').map(r => r.nev);
if (!nevek.length) throw new Error('A háztartásban nincs kiadás-kategória');
const lista = nevek.map(n => JSON.stringify(n)).join('|');
const body = JSON.parse(JSON.stringify(e.anthropic_body));
const szoveg = body.messages[0].content[1];
szoveg.text = szoveg.text.replace('__KAT__', lista) + ' A kategória KIZÁRÓLAG a felsoroltak egyike lehet.';
return [{ json: { anthropic_body: body } }];
"""
ERTELMEZ = HZ_JS + r"""
const e = $('Előkészítés').first().json;
const kats = $('Kategóriák').all().flatMap(i => i.json.results || []);
const KAT = Object.fromEntries(kats.map(r => [r.nev, r.id]));
const EGYEB = KAT['Egyéb'] || (kats.find(r => r.tipus?.value === 'kiadas') || kats[0] || {}).id;
if (!EGYEB) throw new Error('A háztartásban nincs kategória');
let a;
try { a = JSON.parse(((($input.first().json.content || []).find(b => b.type === 'text'))?.text || '').replace(/```json|```/g, '').trim()); } catch (x) { throw new Error('A nyugta nem olvasható'); }
const osszeg = Number(a.osszeg);
if (!isFinite(osszeg) || osszeg <= 0) throw new Error('A nyugta végösszege nem olvasható');
let bontas = (a.bontott_tetelek || []).filter(t => KAT[t.kategoria] && Number(t.osszeg) > 0).map(t => ({ kategoria: t.kategoria, osszeg: Number(t.osszeg) }));
// kategóriánként összevonva (a nyugta soronkénti tételeiből)
const csoport = {};
for (const t of bontas) csoport[t.kategoria] = (csoport[t.kategoria] || 0) + t.osszeg;
bontas = Object.entries(csoport).map(([kategoria, osszeg]) => ({ kategoria, osszeg }));
if (!bontas.length) bontas = [{ kategoria: 'Egyéb', osszeg }];
const fo = [...bontas].sort((x, y) => y.osszeg - x.osszeg)[0];
const ma = new Date().toISOString().slice(0, 10);
// Egy nyomtatott dátum lehetséges értelmezései (ÉÉÉÉ.HH.NN, NN.HH.ÉÉÉÉ; kétjegyű évnél ÉÉ.HH.NN és NN.HH.ÉÉ is)
const jeloltek = (szoveg) => {
  const m = String(szoveg || '').match(/(\d{1,4})\D+(\d{1,2})\D+(\d{1,4})/);
  if (!m) return [];
  const [x, y, z] = [m[1], m[2], m[3]];
  const ki = [];
  const add = (ev, ho, nap) => {
    ev = +ev; ho = +ho; nap = +nap;
    if (ev < 100) ev += 2000;
    const d = new Date(Date.UTC(ev, ho - 1, nap));
    if (d.getUTCFullYear() === ev && d.getUTCMonth() === ho - 1 && d.getUTCDate() === nap) ki.push(d.toISOString().slice(0, 10));
  };
  if (x.length === 4) add(x, y, z);
  else if (z.length === 4) add(z, y, x);
  else { add(x, y, z); add(z, y, x); }
  return ki;
};
const napokMa = (iso) => (Date.parse(ma) - Date.parse(iso)) / 864e5;
const elfogadhato = [...(Array.isArray(a.datumok) ? a.datumok : []).flatMap(jeloltek), ...jeloltek(a.datum)]
  .filter(d => { const k = napokMa(d); return k >= -2 && k <= 400; })
  .sort((p, q) => Math.abs(napokMa(p)) - Math.abs(napokMa(q)));
let datum = elfogadhato[0] || (/^\d{4}-\d{2}-\d{2}$/.test(a.datum || '') ? a.datum : ma);
let datumJegyzet = '';
const kulonbseg = (Date.parse(ma) - Date.parse(datum)) / 864e5;  // napokban
if (isNaN(kulonbseg) || kulonbseg > 400 || kulonbseg < -2) {
  // valószínűtlen dátum (rossz olvasás vagy régi nyugta): a mai nap, az eredetit a megjegyzésbe írjuk
  datumJegyzet = `A nyugtán olvasott dátum: ${a.datum || '?'} (ellenőrizd)`;
  datum = ma;
}
const mod = ['kartya', 'keszpenz', 'atutalas'].includes(a.fizetesi_mod) ? a.fizetesi_mod : 'kartya';
const kereskedo = String(a.kereskedo || 'Ismeretlen').slice(0, 200);
const megj = [e.megj, bontas.length > 1 ? bontas.map(t => t.osszeg + ' ' + t.kategoria).join(', ') : '', datumJegyzet].filter(Boolean).join(' | ');
return [{ json: { valasz: { kereskedo, osszeg, datum, fizetesi_mod: mod, allapot: mod === 'keszpenz' ? 'lezart' : 'banki_egyeztetesre_var', bontott_tetelek: bontas },
  sor: { haztartas: HZ, kereskedo, datum, osszeg, kategoria_id: [KAT[fo.kategoria] || EGYEB], tipus: 'kiadas', tulajdonos: e.feltolto, fizetesi_mod: mod,
         forras: 'nyugta_foto', allapot: mod === 'keszpenz' ? 'lezart' : 'banki_egyeztetesre_var', megjegyzes: megj } } }];
"""
nodes = [
    webhook('Webhook', 'nyugta-feltoltes', 'POST', (0, 0)),
    code('Előkészítés', ELOKESZIT, (240, 0), hiba_ag=True),
    http('Kategóriák', 'GET', f"={BR}{T['kategoriak']}/?user_field_names=true&size=200{HZ_SZURO}", (360, 0), creds=cred_baserow(), lapozas=True, hiba_ag=True),
    code('Haiku kérés', KERES, (420, 0), hiba_ag=True),
    http('Haiku nyugtaolvasás', 'POST', 'https://api.anthropic.com/v1/messages', (480, 0), body='={{ JSON.stringify($json.anthropic_body) }}',
         creds={'httpHeaderAuth': {'id': CRED[HAIKU_NEV], 'name': HAIKU_NEV}}, fejlec={'anthropic-version': '2023-06-01'}, retry=True, hiba_ag=True),
    code('Értelmezés', ERTELMEZ, (720, 0), hiba_ag=True),
    http('Tranzakció rögzítése', 'POST', f"{BR}{T['tranzakciok']}/?user_field_names=true", (960, 0),
         body='={{ JSON.stringify($json.sor) }}', creds=cred_baserow(), hiba_ag=True),
    respond('Válasz', "={{ { status: 'success', data: { ...$('Értelmezés').first().json.valasz, tranzakcio_id: String($json.id) } } }}", (1200, 0)),
    hiba_valasz((720, 240)),
]
k = {}
for a, b in [('Webhook', 'Előkészítés'), ('Előkészítés', 'Kategóriák'), ('Kategóriák', 'Haiku kérés'), ('Haiku kérés', 'Haiku nyugtaolvasás'), ('Haiku nyugtaolvasás', 'Értelmezés'),
             ('Értelmezés', 'Tranzakció rögzítése'), ('Tranzakció rögzítése', 'Válasz')]: osszekot(k, a, b)
for n in ('Előkészítés', 'Kategóriák', 'Haiku kérés', 'Haiku nyugtaolvasás', 'Értelmezés', 'Tranzakció rögzítése'): osszekot(k, n, 'Hiba válasz', 1)
telepit('VeSpendo – Nyugta feltöltés', nodes, k)

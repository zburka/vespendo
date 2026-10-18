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
  'Olvasd végig a nyugta MINDEN sorát, és sorold a termékeket a kategóriák egyikébe a termék jellege alapján (pl. étel, ital, élelmiszer = Élelmiszer; ruha, cipő, textil = Ruházat; ' +
  'tisztítószer, mosogatószer, papírtermék, edény, izzó, háztartási kisgép, kerti és barkács cikk = Háztartás; drogéria és kozmetikum = Háztartás; gyógyszer, vitamin = Egészség; ha a listán nincs ilyen kategória, a legközelebbi illőt vagy az Egyéb-et használd). ' +
  'A kedvezményeket (negatív sorokat) vond le az érintett termék kategóriájából. A bontott_tetelek összege egyezzen a végösszeggel. ' +
  (megj ? 'A felhasználó megjegyzése a tételbontásról (ezt használd elsődlegesen, az összegek összege a végösszeg): "' + megj + '". ' : '');
return [{ json: { hz: HZ, feltolto, megj, anthropic_body: { model: 'claude-haiku-5-5', max_tokens: 900, thinking: { type: 'disabled' }, messages: [{ role: 'user', content: [
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
// a bontás összege pontosan a végösszeg legyen (a modell kerekítései, kedvezmények miatt eltérhet)
const bontasOssz = bontas.reduce((t, x) => t + x.osszeg, 0);
let reszek = bontas.map(t => ({ kategoria: t.kategoria, osszeg: Math.round(t.osszeg * osszeg / bontasOssz * 100) / 100 })).sort((x, y) => y.osszeg - x.osszeg);
const elteres = Math.round((osszeg - reszek.reduce((t, x) => t + x.osszeg, 0)) * 100) / 100;
reszek[0].osszeg = Math.round((reszek[0].osszeg + elteres) * 100) / 100;
const csoportId = 'ny-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
const megj = [e.megj, reszek.length > 1 ? `Nyugta szerinti bontás (összesen ${osszeg} Ft)` : '', datumJegyzet].filter(Boolean).join(' | ');
const allapot = mod === 'keszpenz' ? 'lezart' : 'banki_egyeztetesre_var';
return [{ json: { valasz: { kereskedo, osszeg, datum, fizetesi_mod: mod, allapot, bontott_tetelek: reszek },
  csoport: csoportId,
  sorok: reszek.map(t => ({ haztartas: HZ, kereskedo, datum, osszeg: t.osszeg, kategoria_id: [KAT[t.kategoria] || EGYEB], tipus: 'kiadas', tulajdonos: e.feltolto,
    fizetesi_mod: mod, forras: 'nyugta_foto', allapot, megjegyzes: megj, nyugta_csoport: csoportId })) } }];
"""
TERV = r"""
// ha a bankból már megérkezett a tétel (azonos összeg, a nyugta napja körül), azt bontjuk fel a nyugta szerint; különben a nyugta várakozó tételként
// kerül be, és a későbbi banki import az összegük alapján párosítja a csoportot
const e = $('Értelmezés').first().json;
const v = e.valasz;
const nap = (a, b) => (Date.parse(b) - Date.parse(a)) / 864e5;
const jeloltek = $('Jelöltek').all().flatMap(i => i.json.results || []);
const bank = v.fizetesi_mod === 'keszpenz' ? null : jeloltek
  .filter(r => r.forras?.value === 'bank_import' && !r.nyugta_csoport && r.tipus?.value === 'kiadas' && r.datum && nap(v.datum, r.datum) >= -1 && nap(v.datum, r.datum) <= 7)
  .sort((x, y) => Math.abs(nap(v.datum, x.datum)) - Math.abs(nap(v.datum, y.datum)))[0];
const tabla = '%(tr)s';
const lepesek = [];
if (bank) {
  const elso = e.sorok[0], tobbi = e.sorok.slice(1);
  lepesek.push({ m: 'PATCH', u: `${tabla}${bank.id}/?user_field_names=true`, b: { osszeg: elso.osszeg, kategoria_id: elso.kategoria_id, nyugta_csoport: e.csoport,
    megjegyzes: [bank.megjegyzes, elso.megjegyzes].filter(Boolean).join(' | ').slice(0, 1000) } });
  if (tobbi.length) lepesek.push({ m: 'POST', u: `${tabla}batch/?user_field_names=true`, b: { items: tobbi.map(t => ({ ...t, datum: bank.datum, kereskedo: bank.kereskedo, forras: 'bank_import', allapot: 'lezart' })) } });
} else {
  lepesek.push({ m: 'POST', u: `${tabla}batch/?user_field_names=true`, b: { items: e.sorok } });
}
return lepesek.map(l => ({ json: { ...l, parositva: !!bank, tranzakcio_id: bank ? String(bank.id) : '' } }));
""" % {'tr': BR + str(T['tranzakciok']) + '/'}
VALASZ = r"""
const e = $('Értelmezés').first().json;
const t = $('Terv').first().json;
let id = t.tranzakcio_id;
if (!id) { for (const i of $('Végrehajtás').all()) if (Array.isArray(i.json.items) && i.json.items.length) { id = String(i.json.items[0].id); break; } }
if (!id) throw new Error('A tétel rögzítése nem sikerült');
return [{ json: { status: 'success', data: { ...e.valasz, tranzakcio_id: id, parositva: !!t.parositva } } }];
"""
nodes = [
    webhook('Webhook', 'nyugta-feltoltes', 'POST', (0, 0)),
    code('Előkészítés', ELOKESZIT, (240, 0), hiba_ag=True),
    http('Kategóriák', 'GET', f"={BR}{T['kategoriak']}/?user_field_names=true&size=200{HZ_SZURO}", (360, 0), creds=cred_baserow(), lapozas=True, hiba_ag=True),
    code('Haiku kérés', KERES, (420, 0), hiba_ag=True),
    http('Haiku nyugtaolvasás', 'POST', 'https://api.anthropic.com/v1/messages', (480, 0), body='={{ JSON.stringify($json.anthropic_body) }}',
         creds={'httpHeaderAuth': {'id': CRED[HAIKU_NEV], 'name': HAIKU_NEV}}, fejlec={'anthropic-version': '2023-06-01'}, retry=True, hiba_ag=True),
    code('Értelmezés', ERTELMEZ, (720, 0), hiba_ag=True),
    http('Jelöltek', 'GET', f"={BR}{T['tranzakciok']}/?user_field_names=true&size=200{HZ_SZURO}&filter__osszeg__equal=" + "{{ $('Értelmezés').first().json.valasz.osszeg }}",
         (840, 0), creds=cred_baserow(), lapozas=True, hiba_ag=True),
    code('Terv', TERV, (960, 0), hiba_ag=True),
    node('Végrehajtás', 'n8n-nodes-base.httpRequest', 4.2, {
        'method': '={{ $json.m }}', 'url': '={{ $json.u }}', 'authentication': 'genericCredentialType', 'genericAuthType': 'httpHeaderAuth',
        'sendBody': True, 'specifyBody': 'json', 'jsonBody': '={{ JSON.stringify($json.b || {}) }}', 'options': {}}, (1080, 0), cred_baserow()),
    code('Válasz összeállítása', VALASZ, (1200, 0), hiba_ag=True),
    respond('Válasz', '={{ $json }}', (1320, 0)),
    hiba_valasz((720, 240)),
]
k = {}
for a, b in [('Webhook', 'Előkészítés'), ('Előkészítés', 'Kategóriák'), ('Kategóriák', 'Haiku kérés'), ('Haiku kérés', 'Haiku nyugtaolvasás'), ('Haiku nyugtaolvasás', 'Értelmezés'),
             ('Értelmezés', 'Jelöltek'), ('Jelöltek', 'Terv'), ('Terv', 'Végrehajtás'), ('Végrehajtás', 'Válasz összeállítása'),
             ('Válasz összeállítása', 'Válasz')]: osszekot(k, a, b)
for n in ('Előkészítés', 'Kategóriák', 'Haiku kérés', 'Haiku nyugtaolvasás', 'Értelmezés', 'Jelöltek', 'Terv', 'Válasz összeállítása'): osszekot(k, n, 'Hiba válasz', 1)
telepit('VeSpendo – Nyugta feltöltés', nodes, k)

from n8nlib import *

BR = BASEROW + '/api/database/rows/table/'
KAT_ID = IDS['kategoriak']
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

ELOKESZIT = r"""
const b = $('Webhook').first().json.body || {};
const m = /^data:(image\/(?:jpeg|png|webp|gif));base64,(.+)$/s.exec(String(b.kep_base64 || ''));
if (!m) throw new Error('Hiányzó vagy érvénytelen kep_base64');
const feltolto = b.feltolto === 'feleseg' ? 'feleseg' : 'ferj';
const megj = String(b.megjegyzes || '').slice(0, 500);
const prompt = 'Magyar pénztári nyugta. Add vissza KIZÁRÓLAG egy JSON objektumként: ' +
  '{"kereskedo": szöveg, "osszeg": a fizetendő végösszeg Ft-ban (szám), "datum": "YYYY-MM-DD" vagy null, "fizetesi_mod": "kartya"|"keszpenz"|"atutalas", ' +
  '"bontott_tetelek": [{"kategoria": "Élelmiszer"|"Rezsi"|"Szórakozás"|"Ruházat"|"Közlekedés"|"Egyéb", "osszeg": szám}]}. ' +
  (megj ? 'A felhasználó megjegyzése a tételbontásról (ezt használd a bontáshoz, az összegek összege a végösszeg): "' + megj + '". ' : 'A bontást a nyugta tételei alapján add meg. ');
return [{ json: { feltolto, megj, anthropic_body: { model: 'claude-haiku-5-5', max_tokens: 500, thinking: { type: 'disabled' }, messages: [{ role: 'user', content: [
  { type: 'image', source: { type: 'base64', media_type: m[1], data: m[2] } }, { type: 'text', text: prompt }] }] } } }];
"""
ERTELMEZ = r"""
const e = $('Előkészítés').first().json;
const KAT = %(kat)s;
let a;
try { a = JSON.parse(((($input.first().json.content || []).find(b => b.type === 'text'))?.text || '').replace(/```json|```/g, '').trim()); } catch (x) { throw new Error('A nyugta nem olvasható'); }
const osszeg = Number(a.osszeg);
if (!isFinite(osszeg) || osszeg <= 0) throw new Error('A nyugta végösszege nem olvasható');
let bontas = (a.bontott_tetelek || []).filter(t => KAT[t.kategoria] && Number(t.osszeg) > 0).map(t => ({ kategoria: t.kategoria, osszeg: Number(t.osszeg) }));
if (!bontas.length) bontas = [{ kategoria: 'Egyéb', osszeg }];
const fo = [...bontas].sort((x, y) => y.osszeg - x.osszeg)[0];
const datum = /^\d{4}-\d{2}-\d{2}$/.test(a.datum || '') ? a.datum : new Date().toISOString().slice(0, 10);
const mod = ['kartya', 'keszpenz', 'atutalas'].includes(a.fizetesi_mod) ? a.fizetesi_mod : 'kartya';
const kereskedo = String(a.kereskedo || 'Ismeretlen').slice(0, 200);
const megj = [e.megj, bontas.length > 1 ? bontas.map(t => t.osszeg + ' ' + t.kategoria).join(', ') : ''].filter(Boolean).join(' | ');
return [{ json: { valasz: { kereskedo, osszeg, datum, fizetesi_mod: mod, allapot: 'banki_egyeztetesre_var', bontott_tetelek: bontas },
  sor: { kereskedo, datum, osszeg, kategoria_id: [KAT[fo.kategoria]], tipus: 'kiadas', tulajdonos: e.feltolto, fizetesi_mod: mod,
         forras: 'nyugta_foto', allapot: 'banki_egyeztetesre_var', megjegyzes: megj } } }];
""" % {'kat': json.dumps(KAT_ID, ensure_ascii=False)}
nodes = [
    webhook('Webhook', 'nyugta-feltoltes', 'POST', (0, 0)),
    code('Előkészítés', ELOKESZIT, (240, 0), hiba_ag=True),
    http('Haiku nyugtaolvasás', 'POST', 'https://api.anthropic.com/v1/messages', (480, 0), body='={{ JSON.stringify($json.anthropic_body) }}',
         creds={'httpHeaderAuth': {'id': CRED[HAIKU_NEV], 'name': HAIKU_NEV}}, fejlec={'anthropic-version': '2023-06-01'}, retry=True, hiba_ag=True),
    code('Értelmezés', ERTELMEZ, (720, 0), hiba_ag=True),
    http('Tranzakció rögzítése', 'POST', f"{BR}{T['tranzakciok']}/?user_field_names=true", (960, 0),
         body='={{ JSON.stringify($json.sor) }}', creds=cred_baserow(), hiba_ag=True),
    respond('Válasz', "={{ { status: 'success', data: { ...$('Értelmezés').first().json.valasz, tranzakcio_id: String($json.id) } } }}", (1200, 0)),
    hiba_valasz((720, 240)),
]
k = {}
for a, b in [('Webhook', 'Előkészítés'), ('Előkészítés', 'Haiku nyugtaolvasás'), ('Haiku nyugtaolvasás', 'Értelmezés'),
             ('Értelmezés', 'Tranzakció rögzítése'), ('Tranzakció rögzítése', 'Válasz')]: osszekot(k, a, b)
for n in ('Előkészítés', 'Haiku nyugtaolvasás', 'Értelmezés', 'Tranzakció rögzítése'): osszekot(k, n, 'Hiba válasz', 1)
telepit('VeSpendo – Nyugta feltöltés', nodes, k)

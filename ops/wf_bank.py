"""Banki összekötés (Enable Banking) n8n workflow-i: összekötés indítása, callback, szinkron, állapot, ütemező.
A BANK_URL környezeti változóval átirányítható (teszt: a próbaüzemmódú konténer)."""
import os
from n8nlib import *

BANK_URL = os.environ.get('BANK_URL', 'http://vespendo-bank:8000')
BANK = {'httpHeaderAuth': {'id': CRED['VeSpendo Bank (API key)'], 'name': 'VeSpendo Bank (API key)'}}
APPKULCS = {'httpHeaderAuth': {'id': CRED['VeSpendo App (X-App-Key)'], 'name': 'VeSpendo App (X-App-Key)'}}
TK = T['bankkapcsolatok']
HZ_VAGY_MIND = "{{ (() => { const h = String((($('Webhook').first().json.headers) || {})['x-haztartas'] || ''); if (h === '*') return ''; if (!/^hz_[a-z0-9]{3,40}$/.test(h)) throw new Error('Hiányzó háztartás'); return '&filter__haztartas__equal=' + h; })() }}"
IGAZ = {'type': 'boolean', 'operation': 'true', 'singleValue': True}

# ---------------------------------------------------------------- 1) összekötés indítása
ELO = HZ_JS + r"""
const szemely = String(($('Webhook').first().json.body || {}).szemely || SZEMELY);
if (!/^[a-z0-9_]{1,30}$/.test(szemely) || szemely === 'kozos') throw new Error('Érvénytelen személy');
return [{ json: { hz: HZ, szemely } }];
"""
SZEMELY_ELL = HZ_JS + r"""
const e = $('Előkészítés').first().json;
const sorok = $input.all().flatMap(i => i.json.results || []);
if (!sorok.some(r => r.kulcs === e.szemely && r.aktiv)) throw new Error('Nincs ilyen személy a háztartásban');
const sor = sorok.find(r => r.kulcs === e.szemely);
const alk = String(sor.bank_alkalmazas || 'alap');
if (!/^[a-z0-9_]{1,20}$/.test(alk)) throw new Error('Érvénytelen banki alkalmazás');
return [{ json: { ...e, alkalmazas: alk } }];
"""
VALASZ1 = r"""
const v = $input.first().json;
if (v.statusCode !== 200 || v.body?.status !== 'success' || !v.body?.url) throw new Error(v.body?.uzenet || 'A bank nem adott jóváhagyási hivatkozást');
return [{ json: { status: 'success', url: v.body.url, napok: v.body.napok } }];
"""
nodes = [
    webhook('Webhook', 'bank-osszekotes', 'POST', (0, 0)),
    code('Előkészítés', ELO, (240, 0), hiba_ag=True),
    http('Személyek', 'GET', f"={BR}{T['szemelyek']}/?user_field_names=true&size=200{HZ_SZURO}", (360, 0), creds=cred_baserow(), lapozas=True, hiba_ag=True),
    code('Személy ellenőrzés', SZEMELY_ELL, (420, 0), hiba_ag=True),
    http('Bank /auth', 'POST', f'{BANK_URL}/auth', (480, 0), body="={{ JSON.stringify({ szemely: $json.hz + '~' + $json.szemely, alkalmazas: $json.alkalmazas }) }}", creds=BANK, teljes=True),
    code('Válasz előkészítés', VALASZ1, (720, 0), hiba_ag=True),
    respond('Válasz', '={{ $json }}', (960, 0)),
    hiba_valasz((480, 240)),
]
k = {}
for a, b in [('Webhook', 'Előkészítés'), ('Előkészítés', 'Személyek'), ('Személyek', 'Személy ellenőrzés'), ('Személy ellenőrzés', 'Bank /auth'), ('Bank /auth', 'Válasz előkészítés'), ('Válasz előkészítés', 'Válasz')]: osszekot(k, a, b)
for n in ('Előkészítés', 'Személyek', 'Személy ellenőrzés', 'Válasz előkészítés'): osszekot(k, n, 'Hiba válasz', 1)
telepit('VeSpendo – Bank összekötés indítása', nodes, k)

# ---------------------------------------------------------------- 2) callback (a bank irányít ide vissza)
HTML = r"""
const oldal = (cim, uzenet, ok) => `<!doctype html><html lang="hu"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>VeSpendo</title></head><body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;text-align:center;padding:48px 24px;color:#222">
<div style="font-size:64px">${ok ? '✅' : '⚠️'}</div><h2>${cim}</h2><p style="color:#555;max-width:420px;margin:12px auto">${uzenet}</p>
<p style="color:#888;margin-top:32px">Visszatérhetsz a VeSpendo alkalmazásba.</p></body></html>`;
const esc = (s) => String(s).replace(/[<>&"]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]));
"""
CB_ELO = HTML + r"""
const q = $('Webhook').first().json.query || {};
if (q.error) throw new Error('A jóváhagyás megszakadt vagy elutasítva: ' + (q.error_description || q.error));
if (!q.code || !q.state) throw new Error('Hiányzó jóváhagyási adat a banktól');
return [{ json: { code: String(q.code), state: String(q.state) } }];
"""
CB_SESSION = r"""
const v = $input.first().json;
if (v.statusCode !== 200 || v.body?.status !== 'success' || !(v.body.szamlak || []).length) throw new Error(v.body?.uzenet || 'A bank nem adott vissza számlát');
const [hz, sz] = String(v.body.szemely).split('~');
if (!/^hz_[a-z0-9]{3,40}$/.test(hz || '') || !/^[a-z0-9_]{1,30}$/.test(sz || '')) throw new Error('Érvénytelen állapot a banktól');
return [{ json: { ok: true } }];
"""
CB_ROGZIT = r"""
const s = $('Bank /sessions').first().json.body;
const [hz, szemely] = String(s.szemely).split('~');
const letezo = $input.all().flatMap(i => i.json.results || []);
const uj = [], frissit = [];
for (const a of s.szamlak) {
  const sor = { haztartas: hz, azonosito: `${s.session_id}:${a.uid}`.slice(0, 120), szemely, alkalmazas: s.alkalmazas || 'alap', session_id: s.session_id, szamla_uid: a.uid, iban: a.iban || '', lejarat: s.valid_until || '', aktiv: true };
  // újrajóváhagyáskor a bank új számla-azonosítót adhat: ugyanazon IBAN-hoz tartozó meglévő kapcsolatot frissítjük (nem keletkezik elavult kapcsolat)
const ex = letezo.find(r => r.szamla_uid === a.uid || (a.iban && r.iban === a.iban && r.szemely === szemely));
  if (ex) frissit.push({ id: ex.id, ...sor }); else uj.push({ ...sor, utolso_szinkron: '' });
}
return [{ json: { uj, frissit, szemely, szamlak: s.szamlak.length } }];
"""
CB_HTML = HTML + r"""
const r = $('Rögzítés előkészítés').first().json;
const hibas = (nev, kell) => { if (!kell) return false; try { return $(nev).all().some(i => !Array.isArray(i.json.items)); } catch (e) { return false; } };
if (hibas('Új kapcsolatok mentése', r.uj.length) || hibas('Meglévő kapcsolatok frissítése', r.frissit.length)) throw new Error('A kapcsolat mentése nem sikerült');
return [{ json: { html: oldal('Sikeres összekötés', `A bankszámla összekötése megtörtént (${r.szamlak} számla). A tételek mostantól automatikusan szinkronizálódnak.`, true) } }];
"""
CB_HIBA = HTML + r"""
return [{ json: { html: oldal('Az összekötés nem sikerült', esc($json.error?.message || $json.error || 'Ismeretlen hiba'), false) } }];
"""
html_valasz = node('Válasz', 'n8n-nodes-base.respondToWebhook', 1.1, {'respondWith': 'text', 'responseBody': '={{ $json.html }}',
    'options': {'responseCode': 200, 'responseHeaders': {'entries': [{'name': 'Content-Type', 'value': 'text/html; charset=utf-8'}]}}}, (2200, 0))
nodes = [
    webhook('Webhook', 'bank-callback', 'GET', (0, 0), nyilvanos=True),
    code('Előkészítés', CB_ELO, (240, 0), hiba_ag=True),
    http('Bank /sessions', 'POST', f'{BANK_URL}/sessions', (480, 0), body='={{ JSON.stringify({ code: $json.code, state: $json.state }) }}', creds=BANK, teljes=True),
    code('Session ellenőrzés', CB_SESSION, (720, 0), hiba_ag=True),
    http('Meglévő kapcsolatok', 'GET', f"={BR}{TK}/?user_field_names=true&size=200&filter__haztartas__equal=" + "{{ encodeURIComponent(String($('Bank /sessions').first().json.body.szemely).split('~')[0]) }}", (960, 0), creds=cred_baserow(), lapozas=True),
    code('Rögzítés előkészítés', CB_ROGZIT, (1200, 0), hiba_ag=True),
    http('Új kapcsolatok mentése', 'POST', f"{BR}{TK}/batch/?user_field_names=true", (1440, 0), body='={{ JSON.stringify({ items: $json.uj }) }}', creds=cred_baserow(), never_error=True),
    http('Meglévő kapcsolatok frissítése', 'PATCH', f"{BR}{TK}/batch/?user_field_names=true", (1680, 0),
         body="={{ JSON.stringify({ items: $('Rögzítés előkészítés').first().json.frissit }) }}", creds=cred_baserow(), never_error=True),
    code('Eredmény oldal', CB_HTML, (1920, 0), hiba_ag=True),
    html_valasz,
    code('Hiba oldal', CB_HIBA, (960, 240)),
]
k = {}
for a, b in [('Webhook', 'Előkészítés'), ('Előkészítés', 'Bank /sessions'), ('Bank /sessions', 'Session ellenőrzés'), ('Session ellenőrzés', 'Meglévő kapcsolatok'),
             ('Meglévő kapcsolatok', 'Rögzítés előkészítés'), ('Rögzítés előkészítés', 'Új kapcsolatok mentése'),
             ('Új kapcsolatok mentése', 'Meglévő kapcsolatok frissítése'), ('Meglévő kapcsolatok frissítése', 'Eredmény oldal'),
             ('Eredmény oldal', 'Válasz'), ('Hiba oldal', 'Válasz')]: osszekot(k, a, b)
for n in ('Előkészítés', 'Session ellenőrzés', 'Rögzítés előkészítés', 'Eredmény oldal'): osszekot(k, n, 'Hiba oldal', 1)
telepit('VeSpendo – Bank callback', nodes, k)

# ---------------------------------------------------------------- 3) szinkron
AKTIV = r"""
const sorok = $input.all().flatMap(i => i.json.results || []);
const aktiv = sorok.filter(r => r.aktiv && r.szamla_uid && (!r.lejarat || Date.parse(r.lejarat) > Date.now()));
const lejart = sorok.filter(r => r.aktiv && r.lejarat && Date.parse(r.lejarat) <= Date.now()).length;
if (!aktiv.length) return [{ json: { nincs: true, lejart } }];
return aktiv.map(r => {
  // a bank legfeljebb 89 napnyi történetet ad vissza: 88 nap a felső határ (első szinkron és hosszú kihagyás után is)
  const legkorabbi = Date.now() - 88 * 864e5;
  const alap = new Date(Math.max(r.utolso_szinkron ? Date.parse(r.utolso_szinkron) - 7 * 864e5 : legkorabbi, legkorabbi));
  return { json: { nincs: false, id: r.id, hz: r.haztartas, alkalmazas: r.alkalmazas || 'alap', szemely: r.szemely, uid: r.szamla_uid, utolso: r.utolso_szinkron || '', date_from: alap.toISOString().slice(0, 10) } };
});
"""
IMPORT_ELO = r"""
const kapcs = $('Aktív kapcsolatok').all();
return $input.all().map((it, i) => {
  const k = kapcs[i].json, v = it.json;
  const ok = v.statusCode === 200 && v.body?.status === 'success';
  return { json: { id: k.id, hz: k.hz, szemely: k.szemely, utolso: k.utolso, ok, hiba: ok ? '' : (v.body?.uzenet || `Hiba (${v.statusCode})`), tranzakciok: ok ? v.body.tranzakciok : [] } };
});
"""
OSSZEGZES = r"""
const el = $('Import előkészítés').all();
const imp = $('Banki import').all();
const lejart = $('Aktív kapcsolatok').first().json.lejart || 0;
return [{ json: { status: 'success', kapcsolatok: el.map((e, i) => ({ szemely: e.json.szemely, ok: e.json.ok, hiba: e.json.hiba,
  uj: imp[i]?.json?.data?.uj ?? 0, duplikalt: imp[i]?.json?.data?.duplikalt ?? 0, letoltott: e.json.tranzakciok.length })) } }];
"""
nodes = [
    webhook('Webhook', 'bank-szinkron', 'POST', (0, 0)),
    http('Kapcsolatok', 'GET', f"={BR}{TK}/?user_field_names=true&size=200" + HZ_VAGY_MIND, (240, 0), creds=cred_baserow(), lapozas=True, retry=True),
    code('Aktív kapcsolatok', AKTIV, (480, 0)),
    if_('Nincs kapcsolat?', '={{ $json.nincs }}', '', IGAZ, (720, 0)),
    respond('Üres válasz', "={{ { status: 'success', kapcsolatok: [], megjegyzes: 'Nincs aktív banki kapcsolat.' } }}", (960, -120)),
    http('Bank /transactions', 'GET', f"={BANK_URL}/transactions?uid=" + "{{ $json.uid }}&alkalmazas={{ $json.alkalmazas }}&date_from={{ $json.date_from }}", (960, 120), creds=BANK, teljes=True, retry=True),
    code('Import előkészítés', IMPORT_ELO, (1200, 120)),
    http('Banki import', 'POST', f'http://localhost:5678/webhook/{UT_ELOTAG}banki-import', (1440, 120),
         body='={{ JSON.stringify({ feltolto: $json.szemely, tranzakciok: $json.tranzakciok }) }}', creds=APPKULCS, never_error=True,
         fejlec={'X-Haztartas': '={{ $json.hz }}', 'X-Szemely': '={{ $json.szemely }}'}),
    http('Utolsó szinkron mentése', 'PATCH', f"={BR}{TK}/" + "{{ $('Import előkészítés').item.json.id }}/?user_field_names=true", (1680, 120),
         body="={{ JSON.stringify({ utolso_szinkron: $('Import előkészítés').item.json.ok && $json.status === 'success' ? new Date().toISOString().slice(0, 10) : $('Import előkészítés').item.json.utolso }) }}",
         creds=cred_baserow(), never_error=True),
    code('Összegzés', OSSZEGZES, (1920, 120)),
    respond('Válasz', '={{ $json }}', (2160, 120)),
]
k = {}
for a, b in [('Webhook', 'Kapcsolatok'), ('Kapcsolatok', 'Aktív kapcsolatok'), ('Aktív kapcsolatok', 'Nincs kapcsolat?')]: osszekot(k, a, b)
osszekot(k, 'Nincs kapcsolat?', 'Üres válasz', 0); osszekot(k, 'Nincs kapcsolat?', 'Bank /transactions', 1)
for a, b in [('Bank /transactions', 'Import előkészítés'), ('Import előkészítés', 'Banki import'), ('Banki import', 'Utolsó szinkron mentése'),
             ('Utolsó szinkron mentése', 'Összegzés'), ('Összegzés', 'Válasz')]: osszekot(k, a, b)
telepit('VeSpendo – Bank szinkron', nodes, k, hz_csillag=True)

# ütemező: naponta reggel hívja a szinkront
ut = node('Naponta', 'n8n-nodes-base.scheduleTrigger', 1.2, {'rule': {'interval': [{'field': 'cronExpression', 'expression': '15 6 * * *'}, {'field': 'cronExpression', 'expression': '15 14 * * *'}]}}, (0, 0))
h = http('Szinkron hívása', 'POST', f'http://localhost:5678/webhook/{UT_ELOTAG}bank-szinkron', (260, 0), body='={{ JSON.stringify({}) }}', creds=APPKULCS, never_error=True,
         fejlec={'X-Haztartas': '*'})  # az ütemező minden háztartás kapcsolatát szinkronizálja
k = {}; osszekot(k, 'Naponta', 'Szinkron hívása')
if not UT_ELOTAG:  # párhuzamos kiadásban nem indítunk második ütemezőt (az átálláskor kerül fel)
    telepit('VeSpendo – Bank napi ütemező', [ut, h], k, {'timezone': 'Europe/Budapest'})

# ---------------------------------------------------------------- 4) állapot
ALLAPOT = r"""
const sorok = $input.all().flatMap(i => i.json.results || []);
return [{ json: { kapcsolatok: sorok.filter(r => r.aktiv).map(r => ({
  id: String(r.id), szemely: r.szemely, iban_vege: String(r.iban || '').slice(-4), lejarat: r.lejarat || null,
  napok_hatra: r.lejarat ? Math.floor((Date.parse(r.lejarat) - Date.now()) / 864e5) : null, utolso_szinkron: r.utolso_szinkron || null,
  lejart: !!r.lejarat && Date.parse(r.lejarat) <= Date.now() })) } }];
"""
nodes = [
    webhook('Webhook', 'bank-allapot', 'GET', (0, 0)),
    http('Kapcsolatok', 'GET', f"={BR}{TK}/?user_field_names=true&size=200{HZ_SZURO}", (240, 0), creds=cred_baserow(), lapozas=True),
    code('Összeállítás', ALLAPOT, (480, 0)),
    respond('Válasz', '={{ $json }}', (720, 0)),
]
k = {}
for a, b in [('Webhook', 'Kapcsolatok'), ('Kapcsolatok', 'Összeállítás'), ('Összeállítás', 'Válasz')]: osszekot(k, a, b)
telepit('VeSpendo – Bank állapot', nodes, k)

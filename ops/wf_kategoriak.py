"""Kategóriák kezelése: kategoria-mentes (új / átnevezés / ikon), kategoria-torles (a tételek áthelyezésével)."""
from n8nlib import *

VAN = {'type': 'string', 'operation': 'notEmpty', 'singleValue': True}
KAT_URL = f"={BR}{T['kategoriak']}/?user_field_names=true&size=200{HZ_SZURO}"

# ---------- POST /webhook/kategoria-mentes {id?, nev, tipus? (csak újnál), ikon?}
MENTES_ELO = HZ_JS + r"""
const b = $('Webhook').first().json.body || {};
const nev = String(b.nev || '').trim();
if (!nev || nev.length > 40) throw new Error('A kategória neve kötelező (legfeljebb 40 karakter)');
const id = b.id === undefined || b.id === null ? '' : String(b.id);
if (id && !/^\d+$/.test(id)) throw new Error('Érvénytelen id');
const tipus = String(b.tipus || 'kiadas');
if (!id && !['kiadas', 'bevetel'].includes(tipus)) throw new Error('Érvénytelen típus');
const ikon = b.ikon === undefined ? '' : String(b.ikon);
if (ikon && !/^[a-z0-9-]{1,30}$/.test(ikon)) throw new Error('Érvénytelen ikon');
return [{ json: { hz: HZ, id, nev, tipus, ikon } }];
"""
MENTES_DONT = r"""
const e = $('Előkészítés').first().json;
const sorok = $('Kategóriák').all().flatMap(i => i.json.results || []);
const norm = (s) => String(s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
if (sorok.some(r => String(r.id) !== e.id && norm(r.nev) === norm(e.nev))) throw new Error('Már van ilyen nevű kategória');
if (e.id) {
  const sor = sorok.find(r => String(r.id) === e.id);
  if (!sor) throw new Error('Nincs ilyen kategória');
  return [{ json: { ...e, sor_id: e.id, sor: { nev: e.nev, ...(e.ikon ? { ikon: e.ikon } : {}) } } }];
}
if (sorok.length >= 60) throw new Error('Legfeljebb 60 kategória lehet');
return [{ json: { ...e, sor_id: '', sor: { haztartas: e.hz, nev: e.nev, tipus: e.tipus, ikon: e.ikon || 'tag' } } }];
"""
nodes = [
    webhook('Webhook', 'kategoria-mentes', 'POST', (0, 0)),
    code('Előkészítés', MENTES_ELO, (240, 0), hiba_ag=True),
    http('Kategóriák', 'GET', KAT_URL, (480, 0), creds=cred_baserow(), lapozas=True, hiba_ag=True),
    code('Döntés', MENTES_DONT, (720, 0), hiba_ag=True),
    if_('Van id?', '={{ $json.sor_id }}', '', VAN, (960, 0)),
    http('Frissítés', 'PATCH', f"={BR}{T['kategoriak']}/" + "{{ $json.sor_id }}/?user_field_names=true", (1200, -120),
         body='={{ JSON.stringify($json.sor) }}', creds=cred_baserow(), hiba_ag=True),
    http('Létrehozás', 'POST', f"{BR}{T['kategoriak']}/?user_field_names=true", (1200, 120),
         body='={{ JSON.stringify($json.sor) }}', creds=cred_baserow(), hiba_ag=True),
    respond('Válasz', "={{ { status: 'success', id: String($json.id) } }}", (1440, 0)),
    hiba_valasz((480, 240)),
]
k = {}
for a, b in [('Webhook', 'Előkészítés'), ('Előkészítés', 'Kategóriák'), ('Kategóriák', 'Döntés'), ('Döntés', 'Van id?')]: osszekot(k, a, b)
osszekot(k, 'Van id?', 'Frissítés', 0); osszekot(k, 'Van id?', 'Létrehozás', 1)
osszekot(k, 'Frissítés', 'Válasz'); osszekot(k, 'Létrehozás', 'Válasz')
for n in ('Előkészítés', 'Kategóriák', 'Döntés', 'Frissítés', 'Létrehozás'): osszekot(k, n, 'Hiba válasz', 1)
telepit('VeSpendo – Kategória mentés', nodes, k)

# ---------- POST /webhook/kategoria-torles {id, athelyez_id}: a tételek, szabályok, előfizetések a cél kategóriába kerülnek, a keret törlődik
TOR_ELO = HZ_JS + r"""
const b = $('Webhook').first().json.body || {};
const id = String(b.id || ''), cel = String(b.athelyez_id || '');
if (!/^\d+$/.test(id) || !/^\d+$/.test(cel)) throw new Error('Érvénytelen kategória');
if (id === cel) throw new Error('A cél kategória nem lehet ugyanaz');
return [{ json: { hz: HZ, id, cel } }];
"""
TOR_ELLENORZES = r"""
const e = $('Előkészítés').first().json;
const sorok = $('Kategóriák').all().flatMap(i => i.json.results || []);
const forras = sorok.find(r => String(r.id) === e.id), cel = sorok.find(r => String(r.id) === e.cel);
if (!forras || !cel) throw new Error('Nincs ilyen kategória');
if ((forras.tipus?.value) !== (cel.tipus?.value)) throw new Error('A tételeket azonos típusú (kiadás / bevétel) kategóriába lehet áthelyezni');
return [{ json: e }];
"""
TERV = r"""
const e = $('Előkészítés').first().json;
const lista = (nev) => $(nev).all().flatMap(i => i.json.results || []);
const T = %(tablak)s, BR = '%(br)s';
const kotegek = [];
const patch = (tabla, sorok) => {
  for (let i = 0; i < sorok.length; i += 200)
    kotegek.push({ m: 'PATCH', u: `${BR}${T[tabla]}/batch/?user_field_names=true`, b: { items: sorok.slice(i, i + 200).map(r => ({ id: r.id, kategoria_id: [Number(e.cel)] })) } });
};
const tr = lista('Tranzakciók'), sz = lista('Szabályok'), ef = lista('Előfizetések'), kr = lista('Keretek');
patch('tranzakciok', tr); patch('szabalymotor', sz); patch('elofizetesek', ef);
for (let i = 0; i < kr.length; i += 200)
  kotegek.push({ m: 'POST', u: `${BR}${T.koltsegkeretek}/batch-delete/`, b: { items: kr.slice(i, i + 200).map(r => r.id) } });
// utolsó lépés: maga a kategória (csak ha az előzők mind sikerültek: hiba esetén a workflow itt megáll)
kotegek.push({ m: 'DELETE', u: `${BR}${T.kategoriak}/${e.id}/`, b: null });
return kotegek.map((k, i) => ({ json: { ...k, utolso: i === kotegek.length - 1, athelyezett: { tranzakcio: tr.length, szabaly: sz.length, elofizetes: ef.length, keret_torolve: kr.length } } }));
""" % {'tablak': json.dumps(T), 'br': BR}
def kapcsolt_lista(nev, tabla, poz):
    return http(nev, 'GET', f"={BR}{T[tabla]}/?user_field_names=true&size=200{HZ_SZURO}&filter__kategoria_id__link_row_has=" + "{{ $('Előkészítés').first().json.id }}",
                poz, creds=cred_baserow(), lapozas=True, hiba_ag=True)
nodes = [
    webhook('Webhook', 'kategoria-torles', 'POST', (0, 0)),
    code('Előkészítés', TOR_ELO, (240, 0), hiba_ag=True),
    http('Kategóriák', 'GET', KAT_URL, (480, 0), creds=cred_baserow(), lapozas=True, hiba_ag=True),
    code('Ellenőrzés', TOR_ELLENORZES, (720, 0), hiba_ag=True),
    kapcsolt_lista('Tranzakciók', 'tranzakciok', (960, 0)),
    kapcsolt_lista('Szabályok', 'szabalymotor', (1200, 0)),
    kapcsolt_lista('Előfizetések', 'elofizetesek', (1440, 0)),
    kapcsolt_lista('Keretek', 'koltsegkeretek', (1680, 0)),
    code('Terv', TERV, (1920, 0), hiba_ag=True),
    # egyetlen HTTP csomópont, soronként más kéréssel; sorrendben fut, hiba esetén megáll (a kategória törlése az utolsó)
    node('Végrehajtás', 'n8n-nodes-base.httpRequest', 4.2, {
        'method': '={{ $json.m }}', 'url': '={{ $json.u }}', 'authentication': 'genericCredentialType', 'genericAuthType': 'httpHeaderAuth',
        'sendBody': True, 'specifyBody': 'json', 'jsonBody': '={{ JSON.stringify($json.b || {}) }}', 'options': {}}, (2160, 0), cred_baserow()),
    code('Összegzés', "const t = $('Terv').first().json.athelyezett;\nreturn [{ json: { status: 'success', athelyezett: t } }];", (2400, 0)),
    respond('Válasz', '={{ $json }}', (2640, 0)),
    hiba_valasz((480, 240)),
]
k = {}
for a, b in [('Webhook', 'Előkészítés'), ('Előkészítés', 'Kategóriák'), ('Kategóriák', 'Ellenőrzés'), ('Ellenőrzés', 'Tranzakciók'),
             ('Tranzakciók', 'Szabályok'), ('Szabályok', 'Előfizetések'), ('Előfizetések', 'Keretek'), ('Keretek', 'Terv'),
             ('Terv', 'Végrehajtás'), ('Végrehajtás', 'Összegzés'), ('Összegzés', 'Válasz')]: osszekot(k, a, b)
for n in ('Előkészítés', 'Kategóriák', 'Ellenőrzés', 'Tranzakciók', 'Szabályok', 'Előfizetések', 'Keretek', 'Terv'): osszekot(k, n, 'Hiba válasz', 1)
telepit('VeSpendo – Kategória törlés', nodes, k)

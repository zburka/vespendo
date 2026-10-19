"""VeSpendo Baserow séma létrehozása (idempotens): munkaterület, adatbázis, 6 tábla, induló adatok, saját token."""
import json
from common import AKTUALIS, ENV, ENV_FAJL, hivas, jwt

B = ENV['BASEROW_URL']
H = {'Authorization': jwt()}

def api(m, p, body=None):
    st, d = hivas(m, B + p, body, H)
    if st >= 300:
        raise SystemExit(f'HIBA {m} {p}: {st} {d}')
    return d

# --- munkaterület + adatbázis
ws = next((w for w in api('GET', '/api/workspaces/') if w['name'] == 'VeSpendo'), None) or api('POST', '/api/workspaces/', {'name': 'VeSpendo'})
apps = api('GET', '/api/applications/')
db = next((a for a in apps if a['name'] == 'VeSpendo' and a['workspace']['id'] == ws['id']), None) \
    or api('POST', f"/api/applications/workspace/{ws['id']}/", {'name': 'VeSpendo', 'type': 'database'})
tablak = {t['name']: t['id'] for t in db.get('tables', [])}

def tabla(nev, elso_mezo):
    if nev not in tablak:
        t = api('POST', f"/api/database/tables/database/{db['id']}/", {'name': nev, 'data': [[elso_mezo]], 'first_row_header': True})
        tablak[nev] = t['id']
    return tablak[nev]

def mezok(tid):
    return {f['name']: f for f in api('GET', f'/api/database/fields/table/{tid}/')}

def mezo(tid, nev, tipus, **kw):
    if nev not in mezok(tid):
        api('POST', f'/api/database/fields/table/{tid}/', {'name': nev, 'type': tipus, **kw})

def valaszto(*ertekek):
    szinek = ['light-blue', 'light-green', 'light-orange', 'light-red', 'light-gray']
    return {'select_options': [{'value': v, 'color': szinek[i % 5]} for i, v in enumerate(ertekek)]}

SZAM = dict(number_decimal_places=2, number_negative=False)

kat = tabla('kategoriak', 'nev')
mezo(kat, 'tipus', 'single_select', **valaszto('kiadas', 'bevetel', 'atvezetes'))
# meglévő telepítés: az 'atvezetes' típus (belső átvezetés: se kiadás, se bevétel) hozzáadása
_tip = mezok(kat)['tipus']
if 'atvezetes' not in [o['value'] for o in _tip['select_options']]:
    api('PATCH', f"/api/database/fields/{_tip['id']}/", {'select_options': [{'id': o['id'], 'value': o['value'], 'color': o['color']} for o in _tip['select_options']] + [{'value': 'atvezetes', 'color': 'light-gray'}]})
mezo(kat, 'ikon', 'text')

tr = tabla('tranzakciok', 'kereskedo')
mezo(tr, 'datum', 'date', date_format='ISO', date_include_time=False)
mezo(tr, 'osszeg', 'number', **SZAM)
mezo(tr, 'kategoria_id', 'link_row', link_row_table_id=kat, has_related_field=False)
mezo(tr, 'tipus', 'single_select', **valaszto('kiadas', 'bevetel_rendszeres', 'bevetel_egyszeri'))
mezo(tr, 'tulajdonos', 'text')  # a személy kulcsa (szemelyek tábla), pl. kozos / ferj / feleseg / gyerek
mezo(tr, 'fizetesi_mod', 'single_select', **valaszto('kartya', 'keszpenz', 'atutalas'))
mezo(tr, 'forras', 'single_select', **valaszto('bank_import', 'nyugta_foto', 'kezi'))
mezo(tr, 'allapot', 'single_select', **valaszto('lezart', 'banki_egyeztetesre_var'))
mezo(tr, 'megjegyzes', 'long_text')
mezo(tr, 'nyugta_kep_url', 'text')
mezo(tr, 'nyugta_csoport', 'text')  # egy nyugta több kategória-sora közös azonosítója (a banki tétellel együtt párosulnak)
mezo(tr, 'import_kulcs', 'text')  # duplikáció-védelem újraimportnál (datum|osszeg|kereskedo_nyers)

sz = tabla('szabalymotor', 'minta')
mezo(sz, 'kategoria_id', 'link_row', link_row_table_id=kat, has_related_field=False)
mezo(sz, 'alapertelmezett_tulajdonos', 'text')  # üres = az import feltöltője

# --- személyek (a tulajdonos kulcsainak nevei; átnevezhető, bővíthető)
sem = tabla('szemelyek', 'kulcs')
mezo(sem, 'nev', 'text')
mezo(sem, 'aktiv', 'boolean')

# meglévő telepítés: a tulajdonos single_select mezők szöveggé alakítása (az értékek megmaradnak)
for tid, nev in ((tr, 'tulajdonos'), (sz, 'alapertelmezett_tulajdonos')):
    f = mezok(tid)[nev]
    if f['type'] != 'text':
        api('PATCH', f"/api/database/fields/{f['id']}/", {'type': 'text'})

# --- banki kapcsolatok (Enable Banking munkamenetek számlánként)
bk = tabla('bankkapcsolatok', 'azonosito')   # session_id + számla uid
mezo(bk, 'szemely', 'text')                  # a személy kulcsa, akinek a számlája
mezo(bk, 'session_id', 'text')
mezo(bk, 'szamla_uid', 'text')
mezo(bk, 'iban', 'text')
mezo(bk, 'lejarat', 'text')                  # a hozzáférés lejárata (RFC3339)
mezo(bk, 'utolso_szinkron', 'text')          # YYYY-MM-DD
mezo(bk, 'aktiv', 'boolean')
mezo(bk, 'alkalmazas', 'text')               # melyik Enable Banking alkalmazáson keresztül jött létre (üres = alap)
mezo(sem, 'bank_alkalmazas', 'text')         # a személy banki összekötése melyik alkalmazást használja (üres = alap)

kk = tabla('koltsegkeretek', 'nev')
mezo(kk, 'kategoria_id', 'link_row', link_row_table_id=kat, has_related_field=False)
mezo(kk, 'havi_keret', 'number', **SZAM)
mezo(kk, 'aktiv', 'boolean')

ef = tabla('elofizetesek', 'megnevezes')
mezo(ef, 'varhato_osszeg', 'number', **SZAM)
mezo(ef, 'esedekesseg_napja', 'number', number_decimal_places=0, number_negative=False)
mezo(ef, 'kategoria_id', 'link_row', link_row_table_id=kat, has_related_field=False)

ce = tabla('megtakaritasi_celok', 'cel_neve')
mezo(ce, 'celosszeg', 'number', **SZAM)
mezo(ce, 'aktualis_osszeg', 'number', **SZAM)

# --- többháztartásos működés: minden sor egy háztartáshoz tartozik (szöveges azonosító, pl. hz_csalad)
for _t in (kat, tr, sz, sem, bk, kk, ef, ce):
    mezo(_t, 'haztartas', 'text')

# --- felhasználói ötletek (visszajelzés): az app Súgó oldaláról érkeznek, az e-mail mellett itt is megmaradnak
ot = tabla('otletek', 'felhasznalo')
mezo(ot, 'szoveg', 'long_text')
mezo(ot, 'email', 'text')
mezo(ot, 'ido', 'text')
mezo(ot, 'emailben', 'boolean')   # sikerült-e e-mailben értesíteni
mezo(ot, 'haztartas', 'text')

# --- induló adatok (csak üres táblába)
def ures(tid):
    return api('GET', f'/api/database/rows/table/{tid}/?size=1')['count'] == 0

def sorok(tid, items):
    return api('POST', f'/api/database/rows/table/{tid}/batch/?user_field_names=true', {'items': items})['items']

KATEGORIAK = [('Élelmiszer', 'kiadas', 'cart'), ('Rezsi', 'kiadas', 'flash'), ('Szórakozás', 'kiadas', 'film'),
              ('Ruházat', 'kiadas', 'shirt'), ('Étterem', 'kiadas', 'silverware-fork-knife'), ('Közlekedés', 'kiadas', 'car'), ('Egészség', 'kiadas', 'heart-pulse'), ('Előfizetés', 'kiadas', 'calendar-sync'), ('Banki költségek', 'kiadas', 'bank'), ('Háztartás', 'kiadas', 'home-variant'), ('Törlesztés', 'kiadas', 'credit-card-clock'), ('Átutalás', 'kiadas', 'bank-transfer-out'), ('Gazdaság', 'kiadas', 'sprout'),
              ('Belső átvezetés', 'atvezetes', 'swap-horizontal'),
              ('Egyéb', 'kiadas', 'ellipsis-horizontal'), ('Fizetés', 'bevetel', 'cash'), ('Egyéb bevétel', 'bevetel', 'cash-plus')]
# név szerint feltölt (idempotens): a hiányzó kategóriákat létrehozza, a meglévőket nem bántja
def sorok_lista(tid):
    return api('GET', f'/api/database/rows/table/{tid}/?user_field_names=true&size=200')['results']

letezo_kat = {r['nev'] for r in sorok_lista(kat)}
uj_kat = [{'nev': n, 'tipus': t, 'ikon': i} for n, t, i in KATEGORIAK if n not in letezo_kat]
if uj_kat:
    sorok(kat, uj_kat)
kat_id = {r['nev']: r['id'] for r in sorok_lista(kat)}

SZABALYOK = [('lidl', 'Élelmiszer'), ('spar', 'Élelmiszer'), ('tesco', 'Élelmiszer'), ('aldi', 'Élelmiszer'), ('kifli', 'Élelmiszer'),
             ('mvm', 'Rezsi'), ('telekom', 'Rezsi'), ('digi', 'Rezsi'), ('netflix', 'Szórakozás'), ('spotify', 'Szórakozás'),
             ('mol', 'Közlekedés'), ('omv', 'Közlekedés'),
             ('tranzakció költsége', 'Banki költségek'), ('megb.díj', 'Banki költségek'), ('havidíj', 'Banki költségek'),
             ('munkabér', 'Fizetés'),
             ('pekaru', 'Élelmiszer'), ('johnny', 'Étterem'), ('mcd', 'Étterem'), ('kfc', 'Étterem'), ('burger king', 'Étterem'),
             ('pizzeria', 'Étterem'), ('pizza hut', 'Étterem'),
             ('patika', 'Egészség'), ('gyógyszertár', 'Egészség'), ('apple.com/bill', 'Előfizetés'), ('google workspace', 'Előfizetés'),
             ('claude.ai', 'Előfizetés'), ('youtube', 'Előfizetés')]
# meglévő szabályok kategóriájának felülírása (a streaming mostantól Előfizetés)
FELULIR = {'netflix': 'Előfizetés', 'spotify': 'Előfizetés'}
letezo_minta = {str(r['minta']).strip() for r in sorok_lista(sz)}
uj_sz = [{'minta': m, 'kategoria_id': [kat_id[k]]} for m, k in SZABALYOK if m not in letezo_minta]
if uj_sz:
    sorok(sz, uj_sz)
for r in sorok_lista(sz):
    uj_kat_id = kat_id.get(FELULIR.get(r['minta']))
    if uj_kat_id and [x['id'] for x in r['kategoria_id']] != [uj_kat_id]:
        api('PATCH', f"/api/database/rows/table/{sz}/{r['id']}/?user_field_names=true", {'kategoria_id': [uj_kat_id]})

if not sorok_lista(sem):
    sorok(sem, [{'kulcs': 'kozos', 'nev': 'Közös', 'aktiv': True}, {'kulcs': 'ferj', 'nev': 'Férj', 'aktiv': True},
                {'kulcs': 'feleseg', 'nev': 'Feleség', 'aktiv': True}])

# --- saját adatbázis-token a VeSpendo munkaterülethez
tokenek = api('GET', '/api/database/tokens/')
tok = next((t for t in tokenek if t['name'] == 'vespendo-n8n' and t['workspace'] == ws['id']), None) \
    or api('POST', '/api/database/tokens/', {'name': 'vespendo-n8n', 'workspace': ws['id']})

ids = {'workspace': ws['id'], 'database': db['id'], 'tablak': tablak, 'kategoriak': kat_id}
json.dump(ids, open(AKTUALIS / 'ids.json', 'w'), ensure_ascii=False, indent=1)

# a token az env fájlba (nem a kimenetre)
sorok_env = [s for s in open(ENV_FAJL).read().split('\n') if s and not s.startswith(('BASEROW_VESPENDO_TOKEN=', 'BASEROW_DATABASE_ID='))]
sorok_env += [f"BASEROW_VESPENDO_TOKEN={tok['key']}", f"BASEROW_DATABASE_ID={db['id']}"]
open(ENV_FAJL, 'w').write('\n'.join(sorok_env) + '\n')
print('KÉSZ', json.dumps(ids, ensure_ascii=False))

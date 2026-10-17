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
mezo(kat, 'tipus', 'single_select', **valaszto('kiadas', 'bevetel'))
mezo(kat, 'ikon', 'text')

tr = tabla('tranzakciok', 'kereskedo')
mezo(tr, 'datum', 'date', date_format='ISO', date_include_time=False)
mezo(tr, 'osszeg', 'number', **SZAM)
mezo(tr, 'kategoria_id', 'link_row', link_row_table_id=kat, has_related_field=False)
mezo(tr, 'tipus', 'single_select', **valaszto('kiadas', 'bevetel_rendszeres', 'bevetel_egyszeri'))
mezo(tr, 'tulajdonos', 'single_select', **valaszto('kozos', 'ferj', 'feleseg'))
mezo(tr, 'fizetesi_mod', 'single_select', **valaszto('kartya', 'keszpenz', 'atutalas'))
mezo(tr, 'forras', 'single_select', **valaszto('bank_import', 'nyugta_foto', 'kezi'))
mezo(tr, 'allapot', 'single_select', **valaszto('lezart', 'banki_egyeztetesre_var'))
mezo(tr, 'megjegyzes', 'long_text')
mezo(tr, 'nyugta_kep_url', 'text')
mezo(tr, 'import_kulcs', 'text')  # duplikáció-védelem újraimportnál (datum|osszeg|kereskedo_nyers)

sz = tabla('szabalymotor', 'minta')
mezo(sz, 'kategoria_id', 'link_row', link_row_table_id=kat, has_related_field=False)
mezo(sz, 'alapertelmezett_tulajdonos', 'single_select', **valaszto('kozos', 'ferj', 'feleseg'))

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

# --- induló adatok (csak üres táblába)
def ures(tid):
    return api('GET', f'/api/database/rows/table/{tid}/?size=1')['count'] == 0

def sorok(tid, items):
    return api('POST', f'/api/database/rows/table/{tid}/batch/?user_field_names=true', {'items': items})['items']

KATEGORIAK = [('Élelmiszer', 'kiadas', 'cart'), ('Rezsi', 'kiadas', 'flash'), ('Szórakozás', 'kiadas', 'film'),
              ('Ruházat', 'kiadas', 'shirt'), ('Közlekedés', 'kiadas', 'car'), ('Egyéb', 'kiadas', 'ellipsis-horizontal'),
              ('Fizetés', 'bevetel', 'cash')]
if ures(kat):
    sorok(kat, [{'nev': n, 'tipus': t, 'ikon': i} for n, t, i in KATEGORIAK])
kat_id = {r['nev']: r['id'] for r in api('GET', f'/api/database/rows/table/{kat}/?user_field_names=true&size=200')['results']}

SZABALYOK = [('lidl', 'Élelmiszer'), ('spar', 'Élelmiszer'), ('tesco', 'Élelmiszer'), ('aldi', 'Élelmiszer'), ('kifli', 'Élelmiszer'),
             ('mvm', 'Rezsi'), ('telekom', 'Rezsi'), ('digi', 'Rezsi'), ('netflix', 'Szórakozás'), ('spotify', 'Szórakozás'),
             ('mol ', 'Közlekedés'), ('omv', 'Közlekedés')]
if ures(sz):
    sorok(sz, [{'minta': m, 'kategoria_id': [kat_id[k]], 'alapertelmezett_tulajdonos': 'kozos'} for m, k in SZABALYOK])

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

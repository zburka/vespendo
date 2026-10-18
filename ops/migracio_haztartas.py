"""Meglévő adatok háztartáshoz rendelése (idempotens): minden 'haztartas' nélküli sor a megadott háztartáshoz kerül.
Használat: python3 migracio_haztartas.py [haztartas_id]   (alapértelmezett: hz_csalad)
Előtte teljes mentést készít a /root/vespendo-migracio-*.json fájlba."""
import json, sys, time
from urllib.parse import urlparse
from common import ENV, hivas, jwt

HZ = sys.argv[1] if len(sys.argv) > 1 else 'hz_csalad'
B = ENV['BASEROW_URL']
TOKEN = {'Authorization': 'Token ' + ENV['BASEROW_VESPENDO_TOKEN']}
TABLAK = json.load(open(__file__.rsplit('/', 1)[0] + '/ids.json'))['tablak']
JWT = {'Authorization': jwt()}


def api(m, p, body=None, h=TOKEN):
    st, d = hivas(m, B + p, body, h)
    if st >= 300:
        raise SystemExit(f'HIBA {m} {p}: {st} {d}')
    return d


def sorok(tid):
    ki, ut = [], f'/api/database/rows/table/{tid}/?user_field_names=true&size=200'
    while ut:
        d = api('GET', ut)
        ki += d['results']
        ut = (lambda u: u.path + '?' + u.query)(urlparse(d['next'])) if d.get('next') else None
    return ki


# 1) mező hozzáadása, ha hiányzik
for nev, tid in TABLAK.items():
    mezok = {f['name'] for f in api('GET', f'/api/database/fields/table/{tid}/', h=JWT)}
    if 'haztartas' not in mezok:
        api('POST', f'/api/database/fields/table/{tid}/', {'name': 'haztartas', 'type': 'text'}, h=JWT)
        print('mező létrehozva:', nev)

# 2) mentés
mentes = {nev: sorok(tid) for nev, tid in TABLAK.items()}
fajl = f'/root/vespendo-migracio-{time.strftime("%Y%m%d-%H%M%S")}.json'
json.dump(mentes, open(fajl, 'w'), ensure_ascii=False)
print('mentés:', fajl, {k: len(v) for k, v in mentes.items()})

# 3) kitöltés
for nev, tid in TABLAK.items():
    ures = [r['id'] for r in mentes[nev] if not (r.get('haztartas') or '').strip()]
    for i in range(0, len(ures), 200):
        api('PATCH', f'/api/database/rows/table/{tid}/batch/?user_field_names=true',
            {'items': [{'id': x, 'haztartas': HZ} for x in ures[i:i + 200]]})
    print(f'{nev}: {len(ures)} sor -> {HZ}')

# 4) ellenőrzés
for nev, tid in TABLAK.items():
    marad = [r for r in sorok(tid) if r.get('haztartas') != HZ]
    assert not marad, f'{nev}: {len(marad)} sor kimaradt'
print('KÉSZ')

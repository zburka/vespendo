"""Egy háztartás adatainak visszaállítása mentésből (a Baserow-táblákba új sorokként).
Használat: python3 visszaallitas.py <mentés mappa> <forrás háztartás> [<cél háztartás>]
A cél háztartásnak üresnek kell lennie (alapból ugyanaz, mint a forrás: törlés utáni helyreállítás). A kategóriák új azonosítót
kapnak, a hivatkozások (keretek, szabályok, tranzakciók…) ehhez igazodnak. A belépési kapu (auth.db) külön, fájlmásolással állítható vissza."""
import gzip, json, sys
from pathlib import Path
from urllib.parse import urlparse
from common import ENV, hivas

if len(sys.argv) < 3:
    raise SystemExit(__doc__)
MAPPA, FORRAS = Path(sys.argv[1]), sys.argv[2]
CEL = sys.argv[3] if len(sys.argv) > 3 else FORRAS
B = ENV['BASEROW_URL']
TOKEN = {'Authorization': 'Token ' + ENV['BASEROW_VESPENDO_TOKEN']}
TABLAK = json.load(open(Path(__file__).parent / 'ids.json'))['tablak']
SORREND = ['kategoriak', 'szemelyek', 'szabalymotor', 'koltsegkeretek', 'elofizetesek', 'megtakaritasi_celok', 'tranzakciok', 'bankkapcsolatok']
adat = json.load(gzip.open(MAPPA / 'baserow.json.gz', 'rt', encoding='utf-8'))['tablak']


def api(m, ut, body=None):
    st, d = hivas(m, B + ut, body, TOKEN)
    if st >= 300:
        raise SystemExit(f'HIBA {m} {ut}: {st} {d}')
    return d


def van_sor(tid, hz):
    return api('GET', f'/api/database/rows/table/{tid}/?user_field_names=true&size=1&filter__haztartas__equal={hz}')['count']


if any(van_sor(TABLAK[t], CEL) for t in SORREND):
    raise SystemExit(f'A(z) {CEL} háztartásnak már vannak sorai; a visszaállítás üres célba megy (előbb töröld az adatait).')

kat_atkepezes: dict[int, int] = {}
for nev in SORREND:
    sorok = [r for r in adat[nev] if r.get('haztartas') == FORRAS]
    uj = []
    for r in sorok:
        sor = {}
        for k, v in r.items():
            if k in ('id', 'order'):
                continue
            if isinstance(v, dict) and 'value' in v:
                v = v['value']                                   # egyválasztós mező: a szöveges érték
            elif isinstance(v, list) and v and isinstance(v[0], dict) and 'id' in v[0]:
                v = [kat_atkepezes[x['id']] for x in v]          # hivatkozás: az új kategória-azonosítóra
            sor[k] = v
        sor['haztartas'] = CEL
        uj.append(sor)
    letrehozott = []
    for i in range(0, len(uj), 200):
        letrehozott += api('POST', f"/api/database/rows/table/{TABLAK[nev]}/batch/?user_field_names=true", {'items': uj[i:i + 200]})['items']
    if nev == 'kategoriak':
        kat_atkepezes = {s['id']: n['id'] for s, n in zip(sorok, letrehozott)}
    print(f'{nev}: {len(letrehozott)} sor')
print('KÉSZ')

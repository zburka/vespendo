"""Napi mentés: a VeSpendo Baserow-táblái, a belépési kapu adatbázisa, az n8n workflow-k és a titkok.
Használat: python3 mentes.py   (cronból naponta). Kimenet: /root/vespendo-mentesek/ÉÉÉÉHHNN-ÓÓPPMM/ (csak root olvashatja).
Megőrzés: a legutóbbi 14 mentés + a vasárnapiak 8 hétig. A mentés végén ellenőrzi a fájlokat, hiba esetén nem nulla kilépési kóddal áll meg."""
import gzip, io, json, shutil, sqlite3, subprocess, sys, time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from common import ENV, hivas

KIMENET = Path('/root/vespendo-mentesek')
AUTH_DB = Path('/root/vespendo-auth-data/auth.db')
TITKOK = ['/root/.vespendo.env', '/root/.vespendo-auth.env', '/root/.vespendo-bank.env', '/root/.vespendo-secrets']
B = ENV['BASEROW_URL']
TOKEN = {'Authorization': 'Token ' + ENV['BASEROW_VESPENDO_TOKEN']}
TABLAK = json.load(open(Path(__file__).parent / 'ids.json'))['tablak']


def baserow_sorok(tid):
    ki, ut = [], f'/api/database/rows/table/{tid}/?user_field_names=true&size=200'
    while ut:
        st, d = hivas('GET', B + ut, None, TOKEN)
        if st != 200:
            raise SystemExit(f'Baserow hiba ({tid}): {st}')
        ki += d['results']
        ut = (lambda u: u.path + '?' + u.query)(urlparse(d['next'])) if d.get('next') else None
    return ki


def ir_gz(ut: Path, adat):
    with gzip.open(ut, 'wt', encoding='utf-8') as f:
        json.dump(adat, f, ensure_ascii=False)
    ut.chmod(0o600)


def main():
    KIMENET.mkdir(mode=0o700, exist_ok=True)
    cel = KIMENET / datetime.now().strftime('%Y%m%d-%H%M%S')
    cel.mkdir(mode=0o700)
    try:
        # 1) Baserow
        tablak = {nev: baserow_sorok(tid) for nev, tid in TABLAK.items()}
        ir_gz(cel / 'baserow.json.gz', {'kesz': datetime.now().isoformat(timespec='seconds'), 'tablak': tablak})
        # 2) belépési kapu (SQLite online mentés: írás közben is konzisztens)
        if AUTH_DB.exists():
            forras = sqlite3.connect(f'file:{AUTH_DB}?mode=ro', uri=True)
            masolat = sqlite3.connect(cel / 'auth.db')
            forras.backup(masolat)
            ok = masolat.execute('pragma integrity_check').fetchone()[0]
            felh = masolat.execute('select count(*) from felhasznalok').fetchone()[0]
            forras.close(); masolat.close()
            assert ok == 'ok', f'az auth.db mentése sérült: {ok}'
            (cel / 'auth.db').chmod(0o600)
        # 3) n8n workflow-k (hitelesítő titkok nélkül)
        st, w = hivas('GET', ENV['N8N_URL'] + '/api/v1/workflows?limit=250', None, {'X-N8N-API-KEY': ENV['N8N_API_KEY']})
        assert st == 200, f'n8n lista hiba: {st}'
        ir_gz(cel / 'n8n-workflows.json.gz', [x for x in w['data'] if x['name'].startswith('VeSpendo')])
        # 4) titkok (env fájlok, kulcsfájlok)
        letezo = [t for t in TITKOK if Path(t).exists()]
        subprocess.run(['tar', '-czf', str(cel / 'titkok.tar.gz'), *letezo], check=True, stderr=subprocess.DEVNULL)
        (cel / 'titkok.tar.gz').chmod(0o600)
        # ellenőrzés: visszaolvasható és a sorszámok egyeznek
        vissza = json.load(gzip.open(cel / 'baserow.json.gz', 'rt', encoding='utf-8'))['tablak']
        assert {k: len(v) for k, v in vissza.items()} == {k: len(v) for k, v in tablak.items()}, 'a Baserow-mentés nem egyezik'
        jelentes = {k: len(v) for k, v in tablak.items()}
        print('MENTÉS OK', cel.name, jelentes, 'felhasználók:', felh if AUTH_DB.exists() else '-', 'workflow-k:', len(json.load(gzip.open(cel / 'n8n-workflows.json.gz', 'rt'))))
    except BaseException:
        shutil.rmtree(cel, ignore_errors=True)  # félkész mentés ne maradjon
        raise
    forgat()


def forgat():
    mind = sorted(p for p in KIMENET.iterdir() if p.is_dir())
    tarto = set(mind[-14:])
    for p in mind:
        d = datetime.strptime(p.name[:8], '%Y%m%d')
        if d.weekday() == 6 and datetime.now() - d < timedelta(weeks=8):
            tarto.add(p)
    for p in mind:
        if p not in tarto:
            shutil.rmtree(p)


if __name__ == '__main__':
    main()

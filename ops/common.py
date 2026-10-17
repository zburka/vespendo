"""Közös segédek a VeSpendo üzemeltetési scriptekhez (Baserow / n8n API). Titkok a /root/.vespendo.env fájlból."""
import json, os, shlex, urllib.request, urllib.error
from pathlib import Path

AKTUALIS = Path(__file__).parent
ENV_FAJL = os.environ.get("VESPENDO_ENV", "/root/.vespendo.env")

def env():
    out = {}
    for sor in open(ENV_FAJL):
        sor = sor.strip()
        if sor and not sor.startswith('#') and '=' in sor:
            k, v = sor.split('=', 1)
            out[k] = shlex.split(v)[0] if v else ''
    return out

ENV = env()

def hivas(metodus, url, body=None, fejlec=None):
    adat = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=adat, method=metodus, headers={'Content-Type': 'application/json', 'User-Agent': 'curl/8.5.0', 'Accept': 'application/json', **(fejlec or {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            t = r.read()
            return r.status, (json.loads(t) if t else None)
    except urllib.error.HTTPError as e:
        t = e.read()
        try: return e.code, json.loads(t)
        except Exception: return e.code, t[:300].decode(errors='replace')

def jwt():
    st, d = hivas('POST', ENV['BASEROW_URL'] + '/api/user/token-auth/', {'email': ENV['BASEROW_EMAIL'], 'password': ENV['BASEROW_PASSWORD']})
    if st != 200:
        raise SystemExit(f'Baserow belépés sikertelen: {st} {d if isinstance(d, str) else d.get("error")}')
    return 'JWT ' + (d.get('access_token') or d['token'])

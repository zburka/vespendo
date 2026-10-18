"""A VeSpendo workflow-k n8n futási adatainak törlése 24 óránál régebbről (a futások tartalmában banki tételek, nyugták lehetnek).
Sikeres futások adata eleve nem tárolódik (a workflow-beállítás szerint); a hibás futásokét hibakereséshez egy napig őrizzük.
Használat: python3 n8n_tisztit.py [óra]  (cronból naponta)."""
import sys
from datetime import datetime, timedelta, timezone
from common import ENV, hivas

OREK = int(sys.argv[1]) if len(sys.argv) > 1 else 24
N8N, HDR = ENV['N8N_URL'], {'X-N8N-API-KEY': ENV['N8N_API_KEY']}
hatar = datetime.now(timezone.utc) - timedelta(hours=OREK)
st, wf = hivas('GET', f'{N8N}/api/v1/workflows?limit=250', None, HDR)
azon = [w['id'] for w in wf['data'] if w['name'].startswith('VeSpendo')]
torolt = 0
for wid in azon:
    kurzor = ''
    while True:
        st, d = hivas('GET', f'{N8N}/api/v1/executions?workflowId={wid}&limit=100{kurzor}', None, HDR)
        for x in d['data']:
            if datetime.fromisoformat(x['startedAt'].replace('Z', '+00:00')) < hatar:
                if hivas('DELETE', f"{N8N}/api/v1/executions/{x['id']}", None, HDR)[0] < 300:
                    torolt += 1
        if not d.get('nextCursor'):
            break
        kurzor = f"&cursor={d['nextCursor']}"
print(f'n8n futási adatok törölve: {torolt} ({OREK} óránál régebbi, {len(azon)} VeSpendo workflow)')

"""n8n workflow-k generálása és telepítése az n8n public API-n keresztül."""
import json
import os
from common import AKTUALIS, ENV, hivas

N8N = ENV['N8N_URL']
HDR = {'X-N8N-API-KEY': ENV['N8N_API_KEY']}
CRED = json.load(open(AKTUALIS / 'n8n_cred.json'))
IDS = json.load(open(AKTUALIS / 'ids.json'))
BASEROW = ENV['BASEROW_URL']
T = IDS['tablak']

# Párhuzamos (háztartás-szűrős) kiadás: a webhook-útvonalak előtagot, a workflow-nevek utótagot kapnak.
# Alapból nincs előtag (éles); új, párhuzamos kiadáshoz `N8N_UT_ELOTAG=h-`.
UT_ELOTAG = os.environ.get('N8N_UT_ELOTAG', '')
NEV_UTOTAG = ' (háztartás)' if UT_ELOTAG else ''
BR = BASEROW + '/api/database/rows/table/'

# A kapu (auth-service) állítja be az X-Haztartas / X-Szemely fejlécet; az n8n csak ezt hiszi el (a webhookot az app-kulcs védi).
HZ_KIF = ("(() => { const h = String((($('Webhook').first().json.headers) || {})['x-haztartas'] || ''); "
          "if (!/^hz_[a-z0-9]{3,40}$/.test(h)) throw new Error('Hiányzó háztartás'); return h; })()")
HZ_SZURO = "&filter__haztartas__equal={{ " + HZ_KIF + " }}"
HZ_JS = ("""const _hdr = ($('Webhook').first().json.headers || {});
const HZ = String(_hdr['x-haztartas'] || '');
if (!/^hz_[a-z0-9]{3,40}$/.test(HZ)) throw new Error('Hiányzó háztartás');
const SZEMELY = String(_hdr['x-szemely'] || '');
""")

def cred_baserow():
    return {'httpHeaderAuth': {'id': CRED['VeSpendo Baserow (Token)'], 'name': 'VeSpendo Baserow (Token)'}}

def node(nev, tipus, ver, params, poz, creds=None, **extra):
    n = {'name': nev, 'type': tipus, 'typeVersion': ver, 'parameters': params, 'position': list(poz)}
    if creds: n['credentials'] = creds
    n.update(extra)
    return n

def webhook(nev, ut, metodus, poz, nyilvanos=False):
    """Webhook az app kulcsával védve; `nyilvanos=True` csak ott, ahol kívülről (pl. a bank) hívják."""
    ut = UT_ELOTAG + ut
    if nyilvanos:
        return node(nev, 'n8n-nodes-base.webhook', 2, {
            'httpMethod': metodus, 'path': ut, 'authentication': 'none', 'responseMode': 'responseNode', 'options': {}}, poz,
            webhookId=ut)
    return node(nev, 'n8n-nodes-base.webhook', 2, {
        'httpMethod': metodus, 'path': ut, 'authentication': 'headerAuth', 'responseMode': 'responseNode',
        'options': {}}, poz,
        {'httpHeaderAuth': {'id': CRED['VeSpendo App (X-App-Key)'], 'name': 'VeSpendo App (X-App-Key)'}},
        webhookId=ut)

def http(nev, metodus, url, poz, body=None, creds=None, fejlec=None, lapozas=False, teljes=False, never_error=False, retry=False, hiba_ag=False):
    p = {'method': metodus, 'url': url, 'options': {}}
    if creds:
        p['authentication'] = 'genericCredentialType'; p['genericAuthType'] = 'httpHeaderAuth'
    if body is not None:
        p['sendBody'] = True; p['specifyBody'] = 'json'; p['jsonBody'] = body
    if fejlec:
        p['sendHeaders'] = True
        p['headerParameters'] = {'parameters': [{'name': k, 'value': v} for k, v in fejlec.items()]}
    if lapozas:
        p['options']['pagination'] = {'pagination': {
            'paginationMode': 'responseContainsNextURL', 'nextURL': '={{ $response.body.next }}',
            'paginationCompleteWhen': 'other', 'completeExpression': '={{ !$response.body.next }}',
            'limitPagesFetched': True, 'maxRequests': 100}}
    if teljes or never_error:
        p['options']['response'] = {'response': {'neverError': True, 'fullResponse': teljes}}
    extra = {'retryOnFail': True, 'maxTries': 2, 'waitBetweenTries': 1000} if retry else {}
    if hiba_ag: extra['onError'] = 'continueErrorOutput'
    # az oldalakra bontott lekérés (több kimeneti elem) csak egyszer fusson, különben a következő lépések lapokként ismétlődnek
    if lapozas: extra['executeOnce'] = True
    return node(nev, 'n8n-nodes-base.httpRequest', 4.2, p, poz, creds, **extra)

def code(nev, js, poz, mod='runOnceForAllItems', hiba_ag=False):
    return node(nev, 'n8n-nodes-base.code', 2, {'mode': mod, 'jsCode': js}, poz, **({'onError': 'continueErrorOutput'} if hiba_ag else {}))

def if_(nev, bal, jobb, op, poz):
    """IF node (v2): a `bal` kifejezés `op` összehasonlítása. op: 'true' / 'false' booleanre."""
    return node(nev, 'n8n-nodes-base.if', 2, {'conditions': {
        'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'loose'},
        'conditions': [{'id': 'c1', 'leftValue': bal, 'rightValue': jobb, 'operator': op}],
        'combinator': 'and'}, 'options': {}}, poz)

def respond(nev, torzs, poz, kod='200'):
    return node(nev, 'n8n-nodes-base.respondToWebhook', 1.1, {
        'respondWith': 'json', 'responseBody': torzs,
        'options': {'responseCode': int(kod) if isinstance(kod, str) and kod.isdigit() else kod}}, poz)

def osszekot(kapcsolatok, a, b, kimenet=0):
    kapcsolatok.setdefault(a, {'main': []})
    m = kapcsolatok[a]['main']
    while len(m) <= kimenet: m.append([])
    m[kimenet].append({'node': b, 'type': 'main', 'index': 0})

def hz_kapu(nodes, kapcsolatok, csillag=False):
    """Közvetlenül a védett webhook után fail-closed háztartás-ellenőrzés (hiányzó/hamis fejlécnél a workflow hibával leáll).
    Szükséges, mert a Baserow az üres szűrőt figyelmen kívül hagyja, így hiányzó háztartásnál minden sort visszaadna."""
    w = next((n for n in nodes if n['name'] == 'Webhook' and n['type'] == 'n8n-nodes-base.webhook'), None)
    if not w or w['parameters'].get('authentication') == 'none':
        return
    minta = r"/^(hz_[a-z0-9]{3,40}" + (r"|\*" if csillag else "") + r")$/"
    nodes.append(code('Háztartás ellenőrzés', (
        "const h = String((($('Webhook').first().json.headers) || {})['x-haztartas'] || '');\n"
        f"if (!{minta}.test(h)) throw new Error('Hiányzó vagy érvénytelen háztartás');\n"
        "return $input.all();"), (w['position'][0] + 120, w['position'][1] + 80)))
    kapcsolatok['Háztartás ellenőrzés'] = kapcsolatok.get('Webhook', {'main': [[]]})
    kapcsolatok['Webhook'] = {'main': [[{'node': 'Háztartás ellenőrzés', 'type': 'main', 'index': 0}]]}

def telepit(nev, nodes, kapcsolatok, beallitasok=None, hz_csillag=False):
    nev = nev + NEV_UTOTAG
    hz_kapu(nodes, kapcsolatok, hz_csillag)
    wf = {'name': nev, 'nodes': nodes, 'connections': kapcsolatok, 'settings': {
        'executionOrder': 'v1', 'saveDataSuccessExecution': 'none', 'saveDataErrorExecution': 'all', 'saveManualExecutions': False,
        'saveExecutionProgress': False, **(beallitasok or {})}}
    st, lista = hivas('GET', N8N + '/api/v1/workflows?limit=250', fejlec=HDR)
    meglevo = next((w for w in lista['data'] if w['name'] == nev), None)
    if meglevo:
        st, d = hivas('PUT', f"{N8N}/api/v1/workflows/{meglevo['id']}", wf, HDR)
    else:
        st, d = hivas('POST', N8N + '/api/v1/workflows', wf, HDR)
    if st >= 300:
        raise SystemExit(f'telepítés hiba {nev}: {st} {d}')
    wid = d['id']
    st, a = hivas('POST', f'{N8N}/api/v1/workflows/{wid}/activate', fejlec=HDR)
    if st >= 300:
        raise SystemExit(f'aktiválás hiba {nev}: {st} {a}')
    print('OK', nev, wid, 'active=', a.get('active'))
    return wid

def webhook_url(ut):
    return f"{N8N}/webhook/{UT_ELOTAG}{ut}"

def app_hivas(metodus, ut, body=None):
    return hivas(metodus, webhook_url(ut), body, {'X-App-Key': ENV['VESPENDO_APP_KEY']})


def hiba_valasz(poz, nev='Hiba válasz'):
    """400-as, érthető hibaüzenet a hívónak (a hibaágból)."""
    return respond(nev, "={{ { status: 'error', uzenet: String($json.error?.message || $json.error || 'Hiba történt').replace(/\\s*\\[line \\d+\\]\\s*$/, '') } }}", poz, kod='400')


def tulajdon_ellenorzes(nev, tabla, id_kif, poz, elozo='Előkészítés'):
    """Id alapú írás előtt: lekéri a sort, és hibát dob, ha nem a hívó háztartásáé. Kimenet: az `elozo` node adata változatlanul.
    Visszaad: (lekérő node, ellenőrző node) – a hibaág az ellenőrzőn van."""
    g = http(nev + ' lekérés', 'GET', f"={BR}{T[tabla]}/{{{{ {id_kif} }}}}/?user_field_names=true", poz, creds=cred_baserow(), never_error=True)
    c = code(nev + ' ellenőrzés', HZ_JS + """const r = $input.first().json;
if (!r || r.haztartas !== HZ || !r.id) throw new Error('Nincs ilyen elem');
return [{ json: $('ELOZO').first().json }];""".replace('ELOZO', elozo), (poz[0] + 130, poz[1]), hiba_ag=True)
    return g, c

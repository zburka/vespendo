from n8nlib import *

nodes = [
    webhook('Webhook', 'banki-fajl-elemzes', 'POST', (0, 0)),
    http('Python elemző', 'POST', 'http://vespendo-parser:8000/parse', (260, 0),
         body='={{ JSON.stringify({ fajl_nev: $json.body.fajl_nev, fajl_base64: $json.body.fajl_base64 }) }}',
         creds={'httpHeaderAuth': {'id': CRED['VeSpendo Parser (API key)'], 'name': 'VeSpendo Parser (API key)'}},
         teljes=True),
    respond('Válasz', '={{ $json.body }}', (520, 0), kod='={{ $json.statusCode }}'),
]
k = {}
osszekot(k, 'Webhook', 'Python elemző'); osszekot(k, 'Python elemző', 'Válasz')
telepit('VeSpendo – Banki fájl elemzés', nodes, k)

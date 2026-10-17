# Üzemeltetési scriptek (Baserow és n8n)

Kódként leírt infrastruktúra: a VeSpendo Baserow-sémát és az n8n workflow-kat ezek hozzák létre, újrafuttathatók
(idempotensek). A titkokat a `/root/.vespendo.env` fájl tartalmazza (`VESPENDO_ENV` környezeti változóval
felülírható), ez soha nem kerül a repóba.

Szükséges kulcsok: `BASEROW_URL`, `BASEROW_EMAIL`, `BASEROW_PASSWORD`, `N8N_URL`, `N8N_API_KEY`, `PARSER_API_KEY`,
`VESPENDO_APP_KEY` (és a script által létrehozott `BASEROW_VESPENDO_TOKEN`).

```bash
python3 baserow_setup.py        # munkaterület, adatbázis, 6 tábla, induló adatok, saját token
python3 wf_fajl_elemzes.py      # POST /webhook/banki-fajl-elemzes  (-> vespendo-parser konténer)
python3 wf_import.py            # POST /webhook/banki-import
python3 wf_adatok.py            # GET  /webhook/adatok, GET /webhook/tranzakciok?honap=
python3 wf_havi.py              # GET  /webhook/havi-osszesito?honap=
python3 wf_kategoria.py         # POST /webhook/kategoria-modositas
python3 wf_nyugta.py            # POST /webhook/nyugta-feltoltes  (AI hitelesítő nélkül 503-at ad)
```

A webhookok `X-App-Key` fejlécet várnak. A Haiku / Sonnet lépések akkor épülnek be, ha az n8n-ben létezik a
`VeSpendo Anthropic (x-api-key)` hitelesítő (és szerepel az `n8n_cred.json`-ban), majd a workflow scriptek újra lefutnak.
A parser konténer: `docker run -d --name vespendo-parser --network cloudoptima-net -e PARSER_API_KEY=... vespendo-parser`.

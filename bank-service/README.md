# Banki szolgáltatás (Enable Banking)

Az OTP számlák PSD2 alapú, automatikus lekérdezése. Az n8n hívja (belső Docker hálózat), kívülről nem elérhető.
A privát kulcs csak ebben a konténerben van, csak olvashatóan csatolva; az n8n nem látja.

## Futtatás
```bash
docker build -t vespendo-bank bank-service
docker run -d --name vespendo-bank --network cloudoptima-net --restart unless-stopped \
  -e ENABLEBANKING_APP_ID=... -e BANK_API_KEY=... \
  -v /root/.vespendo-secrets/enablebanking.pem:/run/secrets/enablebanking.pem:ro vespendo-bank
```
Tesztelés bank nélkül: `-e BANK_MOCK=1` (hamis bejelentkezés és minta-tételek, nincs külső hívás).

## Végpontok (`X-API-Key` fejléc)
- `GET /ellenorzes`: a kulcs és az alkalmazás ellenőrzése az Enable Banking felé
- `POST /auth {szemely}`: jóváhagyási hivatkozás (OTP Bank, HU, magánszemély); a `state` aláírt és 30 perc alatt lejár
- `POST /sessions {code, state}`: munkamenet a banki visszairányítás kódjából; a számla azonosítója az `uid`
- `GET /transactions?uid&date_from[&date_to]`: a könyvelt (BOOK) tételek a VeSpendo import formátumára alakítva, `kulcs: "eb:<azonosító>"`
- `GET /balances?uid`

## Folyamat
1. Az app a `bank-osszekotes` webhookot hívja, a hivatkozást böngészőben nyitja meg, a jóváhagyás az OTP-appban történik.
2. A bank a `bank-callback` webhookra irányít vissza; az n8n eltárolja a kapcsolatot a Baserow `bankkapcsolatok` táblájában.
3. A `bank-szinkron` naponta fut (06:15), a `banki-import` végponton át tölti be az új tételeket. Az API-s tételek saját
   azonosítót kapnak; a PDF-ből már betöltött, azonos személyű, összegű, irányú és napú (±1) tétel nem duplázódik,
   hanem megkapja a bank azonosítóját.

## Az Enable Banking oldalán szükséges beállítás
- Átirányítási cím (redirect URL): `https://n8n.cloudoptima.hu/webhook/bank-callback`
- A korlátozott éles mód az első számla összekötésekor aktiválódik ("Activate by linking accounts" a vezérlőpulton).
- Az engedély a banki szabályok szerint időszakosan lejár; az app jelzi, mikor kell újra jóváhagyni.

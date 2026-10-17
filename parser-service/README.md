# Banki fájl elemző (parser-service)

Bármilyen banki kivonatot (CSV, XLSX, PDF) egységes tranzakciólistává alakít. **Nem használ AI-t**,
nincs token költség: a tartalom alapján ismeri fel a dátum-, összeg-, partner- és közlemény-oszlopokat,
és ahol van egyenleg oszlop, abból ellenőrzi az összegeket és az irányt (bármely bank formátumára működik).

Korlátok: szkennelt (képes) PDF és régi `.xls` nem támogatott; az összeg nélküli vagy nem táblázatos
PDF-ek nem biztos, hogy olvashatók. Ha a `megbizhatosag` nem `magas`, az app figyelmeztet.

## Futtatás
```bash
pip install -r requirements.txt && pytest
PARSER_API_KEY=titok uvicorn main:app --port 8000     # vagy: docker build -t vespendo-parser .
```

## n8n bekötés
Az app csak az n8n-nel beszél. Új webhook: `POST /webhook/banki-fajl-elemzes`
(body: `{"fajl_nev": "...", "fajl_base64": "..."}`) -> **HTTP Request** node:
`POST http://<parser-host>:8000/parse`, fejléc `X-API-Key`, ugyanaz a body -> **Respond to Webhook**
a szolgáltatás válaszával (siker: `{status:"success", data:{tranzakciok, kihagyott, megbizhatosag,
figyelmeztetesek}}`, hiba: `{status:"error", uzenet}`). A szolgáltatást ne tedd ki az internetre.
A felhasználó jóváhagyása után az app a már meglévő `POST /webhook/banki-import` végpontra küldi a
`tranzakciok` listát.

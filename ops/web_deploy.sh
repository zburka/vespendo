#!/usr/bin/env bash
# A webes (PWA) változat telepítése: build, majd a kiszolgált mappa kicserélése. A konténert nem kell újraindítani,
# a felhasználók a következő megnyitáskor az új verziót kapják.
set -euo pipefail
CEL=/root/vespendo-web
cd "$(dirname "$0")/.."
rm -rf "$CEL/dist.uj"
# A nyilvános csomagba SEMMILYEN titok nem kerülhet: az EXPO_PUBLIC_* értékeket az Expo a csomagba égeti (a .env.local
# fájlból is), ezért itt kifejezetten üresre állítjuk őket. Weben az app a saját eredetét használja, a belépés felhasználónévvel és jelszóval történik.
CI=1 EXPO_PUBLIC_N8N_APP_KEY= EXPO_PUBLIC_N8N_BASE_URL= EXPO_PUBLIC_API_BASE_URL= npx expo export --platform web --output-dir "$CEL/dist.uj"
# ellenőrzés: nincs-e a csomagban egyetlen ismert titok sem
set -a; . /root/.vespendo.env; . <(grep -E '^(AUTH_JWT_TITOK|REGISZTRACIOS_KOD)=' /root/.vespendo-auth.env); set +a
for k in VESPENDO_APP_KEY BANK_API_KEY PARSER_API_KEY BASEROW_VESPENDO_TOKEN ANTHROPIC_API_KEY N8N_API_KEY AUTH_JWT_TITOK REGISZTRACIOS_KOD; do
  v=${!k:-}; [ -n "$v" ] && grep -rqF -- "$v" "$CEL/dist.uj" && { echo "HIBA: a(z) $k a csomagban van, a telepítés leáll, az éles változat érintetlen"; rm -rf "$CEL/dist.uj"; exit 1; }
done
rm -rf "$CEL/dist.regi"
[ -d "$CEL/dist" ] && mv "$CEL/dist" "$CEL/dist.regi"
mv "$CEL/dist.uj" "$CEL/dist"
rm -rf "$CEL/dist.regi"
echo "Telepítve: $CEL/dist ($(date '+%F %T'))"

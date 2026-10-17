#!/usr/bin/env bash
# A webes (PWA) változat telepítése: build, majd a kiszolgált mappa kicserélése. A konténert nem kell újraindítani,
# a felhasználók a következő megnyitáskor az új verziót kapják.
set -euo pipefail
CEL=/root/vespendo-web
cd "$(dirname "$0")/.."
rm -rf "$CEL/dist.uj"
CI=1 npx expo export --platform web --output-dir "$CEL/dist.uj"
rm -rf "$CEL/dist.regi"
[ -d "$CEL/dist" ] && mv "$CEL/dist" "$CEL/dist.regi"
mv "$CEL/dist.uj" "$CEL/dist"
rm -rf "$CEL/dist.regi"
echo "Telepítve: $CEL/dist ($(date '+%F %T'))"

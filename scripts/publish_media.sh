#!/usr/bin/env bash
# Sube los videos y .zip de los días vigentes (ayer en adelante, máx. ~14 días) a la rama `media`.
# La rama se reescribe en cada envío para que el repositorio no crezca sin límite.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_URL="$(git -C "$ROOT" remote get-url origin)"
KEEP_FROM="$(TZ=America/Lima date -d 'yesterday' +%F)"
TMP="$(mktemp -d)"
cd "$TMP"
git init -q -b media
git config user.name "zone-digital-bot"; git config user.email "zone-digital-bot@users.noreply.github.com"
n=0
for d in "$ROOT"/build/20*; do
  day="$(basename "$d")"
  [[ "$day" < "$KEEP_FROM" ]] && continue
  [[ -n "$(ls "$d"/*.mp4 2>/dev/null)" ]] || continue
  mkdir -p "dias/$day"; cp "$d"/*.mp4 "$d"/*.zip "dias/$day/"; n=$((n+1))
done
printf "# Rama media\n\nVideos y .zip de los días vigentes. Se reescribe cada semana. Los copys están en la rama main (dias/).\n" > README.md
git add -A && git commit -qm "Media vigente desde $KEEP_FROM ($n días)"
git push -q -f "$REPO_URL" media:media
echo "media: $n días publicados"
rm -rf "$TMP"

#!/usr/bin/env bash
# Publica en la rama `media` los videos y .zip de los días vigentes (desde ayer, hora Lima).
# Conserva lo que ya estaba publicado para esos días, agrega lo nuevo de build/ y reescribe la rama
# en un único commit para que el repositorio no crezca sin límite.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_URL="$(git -C "$ROOT" remote get-url origin)"
KEEP_FROM="$(TZ=America/Lima date -d 'yesterday' +%F)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 1) lo que ya está publicado
if git ls-remote --exit-code --heads "$REPO_URL" media >/dev/null 2>&1; then
  git clone -q --depth 1 --branch media "$REPO_URL" "$TMP/old"
fi
mkdir -p "$TMP/new/dias"
if [ -d "$TMP/old/dias" ]; then
  for d in "$TMP/old/dias"/20*; do
    day="$(basename "$d")"
    [[ "$day" < "$KEEP_FROM" ]] && continue
    cp -r "$d" "$TMP/new/dias/"
  done
fi
# 2) lo nuevo de build/
for d in "$ROOT"/build/20*; do
  [ -d "$d" ] || continue
  day="$(basename "$d")"
  [[ "$day" < "$KEEP_FROM" ]] && continue
  ls "$d"/*.mp4 >/dev/null 2>&1 || continue
  rm -rf "$TMP/new/dias/$day"; mkdir -p "$TMP/new/dias/$day"
  cp "$d"/*.mp4 "$d"/*.zip "$TMP/new/dias/$day/"
done
# 3) un solo commit, forzado
cd "$TMP/new"
printf "# Rama media\n\nVideos y .zip de los días vigentes. Se reescribe en cada envío. Los copys están en la rama main (dias/).\n" > README.md
git init -q -b media
git config user.name "zone-digital-bot"; git config user.email "zone-digital-bot@users.noreply.github.com"
git add -A && git commit -qm "Media vigente desde $KEEP_FROM"
git push -q -f "$REPO_URL" media:media
echo "media: $(ls dias | wc -l) días publicados ($(ls dias | head -1) → $(ls dias | tail -1))"

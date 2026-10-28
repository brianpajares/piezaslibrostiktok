#!/usr/bin/env python3
"""Actualiza HOY.md con las piezas del día (hora de Lima) e imprime el mensaje corto para Brian.

  python3 scripts/hoy.py            # hoy
  python3 scripts/hoy.py 2026-11-02 # otra fecha
"""
import datetime as dt, json, os, sys
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
date = sys.argv[1] if len(sys.argv) > 1 else dt.datetime.now(ZoneInfo("America/Lima")).date().isoformat()
src = os.path.join(ROOT, "dias", date, "README.md")
if not os.path.exists(src):
    print(f"NO HAY PAQUETE PARA {date}. Hay que generar la semana (scripts/build_days.py).")
    sys.exit(2)
body = open(src, encoding="utf-8").read()
open(os.path.join(ROOT, "HOY.md"), "w", encoding="utf-8").write(
    f"<!-- actualizado automáticamente: {date} -->\n" + body)

plan = json.load(open(os.path.join(ROOT, "content", "plan.json"), encoding="utf-8"))[date]
pool = {p["id"]: p for p in json.load(open(os.path.join(ROOT, "content", "pool.json"), encoding="utf-8"))["pieces"]}
repo = json.load(open(os.path.join(ROOT, "content", "config.json"), encoding="utf-8"))["repo"]
base = f"https://github.com/{repo}/releases/download/{date}"
lines = [f"TikTok hoy {date}: {len(plan)} piezas",
         f"Todo en uno: {base}/{date}.zip",
         f"Copys listos: https://github.com/{repo}/blob/main/dias/{date}/README.md"]
for i, s in enumerate(plan, 1):
    p = pool[s["piece"]]
    hook = p.get("hook") or p["slides"][0]["h"]
    lines.append(f"{i}) {s['time']} · {hook}")
print("\n".join(lines))

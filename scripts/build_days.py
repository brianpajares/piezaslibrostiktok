#!/usr/bin/env python3
"""Arma los paquetes diarios de TikTok (videos + copys + zip) para un rango de fechas.

  python3 scripts/build_days.py --from 2026-10-29 --to 2026-11-04 [--jobs 4] [--release]

Qué hace:
  1. Decide cuántas piezas manuales tiene cada día: 5 menos las que publica Metricool solo (content/config.json).
  2. Asigna piezas de content/pool.json (primero las fechadas para ese día, luego las siguientes, sin repetir libro en el día).
  3. Diseña cada pieza (reel o carrusel en video 9:16) con engine/render.py.
  4. Escribe dias/AAAA-MM-DD/README.md (orden, horas y copys) y build/AAAA-MM-DD/*.mp4 + .zip.
  5. Con --release sube los videos y el zip como Release "AAAA-MM-DD" del repositorio (necesita gh).
"""
import argparse, datetime as dt, json, os, shutil, subprocess, sys, zipfile
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
os.environ.setdefault("ZP_OUT", os.path.join(BUILD, "_render"))
sys.path.insert(0, os.path.join(ROOT, "engine"))
import render  # noqa: E402

CFG = json.load(open(os.path.join(ROOT, "content", "config.json"), encoding="utf-8"))
POOL_F = os.path.join(ROOT, "content", "pool.json")
PLAN_F = os.path.join(ROOT, "content", "plan.json")
DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def jload(p, d):
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else d


def auto_times(date):
    for r in CFG["auto_metricool"]:
        if r["from"] <= date <= r["to"]:
            return r["times"]
    return []


def nice_date(date):
    d = dt.date.fromisoformat(date)
    return f"{DIAS_ES[d.weekday()]} {d.day} {MESES[d.month - 1]}"


def assign(date, pool, plan):
    if date in plan:
        return plan[date]
    used = {s["piece"] for day in plan.values() for s in day}
    auto = auto_times(date)
    times = [t for t in CFG["manual_times"] if t not in auto][: CFG["daily_total"] - len(auto)]
    free = [p for p in pool if p["id"] not in used]
    chosen = [p for p in free if p.get("pref_date") == date]
    rest = [p for p in free if p not in chosen and (not p.get("pref_date") or p["pref_date"] < date)]
    for p in rest:
        if len(chosen) >= len(times):
            break
        if p["book"] not in {c["book"] for c in chosen}:
            chosen.append(p)
    for p in rest:  # if still short, allow a repeated book
        if len(chosen) >= len(times):
            break
        if p not in chosen:
            chosen.append(p)
    if len(chosen) < len(times):
        print(f"!! {date}: faltan {len(times) - len(chosen)} piezas en content/pool.json", file=sys.stderr)
    chosen = chosen[: len(times)]
    # reels first in the morning, carousels mid-day: keep given order but put pref-dated at their slot
    plan[date] = [{"time": t, "piece": p["id"]} for t, p in zip(times, chosen)]
    return plan[date]


def fname(i, slot, p):
    return f"{i:02d}_{slot['time'].replace(':', 'h')}_{p['book']}.mp4"


def render_one(args):
    date, i, slot, p = args
    q = dict(p, day=int(date.replace("-", "")[-4:]) * 10 + i)  # unique temp name
    src = render.render_reel(q) if p["fmt"] == "reel" else render.render_carousel_video(q)
    dst = os.path.join(BUILD, date, fname(i, slot, p))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
    return dst


def write_day(date, slots, byid):
    auto = auto_times(date)
    d = os.path.join(ROOT, "dias", date)
    os.makedirs(d, exist_ok=True)
    base = f"https://github.com/{CFG['repo']}/releases/download/{date}"
    lines = [f"# {nice_date(date)} — {len(slots)} piezas para subir a TikTok", ""]
    if auto:
        lines += [f"> Metricool publica solo a las {', '.join(auto)}. Tú subes estas {len(slots)}.", ""]
    lines += [f"**Descarga todo junto:** [{date}.zip]({base}/{date}.zip)", "",
              "| # | Hora | Libro | Formato | Video |", "|---|---|---|---|---|"]
    for i, s in enumerate(slots, 1):
        p = byid[s["piece"]]; f = fname(i, s, p)
        lines.append(f"| {i} | {s['time']} | {render.CAT['books'][p['book']]['title']} | "
                     f"{'Reel' if p['fmt'] == 'reel' else 'Carrusel (video)'} | [{f}]({base}/{f}) |")
    lines += ["", "## Copys (toca el botón de copiar de cada bloque)", ""]
    copies = []
    for i, s in enumerate(slots, 1):
        p = byid[s["piece"]]
        cap = render.caption(p)
        copies.append((fname(i, s, p).replace(".mp4", ".txt"), cap))
        lines += [f"### {i}. {s['time']} — {render.CAT['books'][p['book']]['title']}", "", "```", cap, "```", ""]
    lines += ["## Cómo subir (≈1 min por pieza)",
              "1. Descarga el video en el celular.", "2. TikTok › **+** › Subir › elige el video.",
              "3. Pega el copy. En **Más opciones** activa *Contenido comercial › Tu marca*.",
              "4. Si tu app muestra **Programar**, deja las piezas programadas a su hora y listo; si no, publícalas a su hora.", ""]
    open(os.path.join(d, "README.md"), "w", encoding="utf-8").write("\n".join(lines))
    for name, cap in copies:
        open(os.path.join(d, name), "w", encoding="utf-8").write(cap + "\n")
    return copies


def make_zip(date, copies):
    folder = os.path.join(BUILD, date)
    for name, cap in copies:
        open(os.path.join(folder, name), "w", encoding="utf-8").write(cap + "\n")
    zp = os.path.join(folder, f"{date}.zip")
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:
        for f in sorted(os.listdir(folder)):
            if f.endswith((".mp4", ".txt")):
                z.write(os.path.join(folder, f), f)
    return zp


def release(date):
    folder = os.path.join(BUILD, date)
    assets = [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.endswith((".mp4", ".zip"))]
    notes = f"Piezas de TikTok para {nice_date(date)}. Copys en dias/{date}/README.md"
    exists = subprocess.run(["gh", "release", "view", date, "--repo", CFG["repo"]],
                            capture_output=True).returncode == 0
    if exists:
        subprocess.run(["gh", "release", "upload", date, *assets, "--clobber", "--repo", CFG["repo"]], check=True)
    else:
        subprocess.run(["gh", "release", "create", date, *assets, "--repo", CFG["repo"],
                        "--title", f"{nice_date(date)} — TikTok", "--notes", notes], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="a", required=True); ap.add_argument("--to", dest="b", required=True)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--release", action="store_true")
    a = ap.parse_args()
    pool = jload(POOL_F, {"pieces": []})["pieces"]; byid = {p["id"]: p for p in pool}
    plan = jload(PLAN_F, {})
    d0, d1 = dt.date.fromisoformat(a.a), dt.date.fromisoformat(a.b)
    dates = [str(d0 + dt.timedelta(days=k)) for k in range((d1 - d0).days + 1)]
    jobs = []
    for date in dates:
        for i, s in enumerate(assign(date, pool, plan), 1):
            jobs.append((date, i, s, byid[s["piece"]]))
    json.dump(plan, open(PLAN_F, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with Pool(min(a.jobs, max(1, len(jobs)))) as pl:
        for r in pl.imap_unordered(render_one, jobs):
            print("ok", os.path.relpath(r, ROOT), flush=True)
    for date in dates:
        copies = write_day(date, plan[date], byid)
        make_zip(date, copies)
        if a.release:
            release(date)
            print("release", date, flush=True)


if __name__ == "__main__":
    main()

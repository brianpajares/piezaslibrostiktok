#!/usr/bin/env python3
"""Arma el correo diario (asunto + HTML + texto) con lo que Brian sube a mano a TikTok e Instagram.

  python3 scripts/email_hoy.py [AAAA-MM-DD] > /tmp/email.json
Salida JSON: {"subject": ..., "html": ..., "text": ...}
"""
import datetime as dt, html, json, os, sys
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
os.environ.setdefault("ZP_OUT", os.path.join(ROOT, "build", "_render"))
import render  # noqa: E402

DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

date = sys.argv[1] if len(sys.argv) > 1 else dt.datetime.now(ZoneInfo("America/Lima")).date().isoformat()
cfg = json.load(open(os.path.join(ROOT, "content", "config.json"), encoding="utf-8"))
plan = json.load(open(os.path.join(ROOT, "content", "plan.json"), encoding="utf-8"))
pool = {p["id"]: p for p in json.load(open(os.path.join(ROOT, "content", "pool.json"), encoding="utf-8"))["pieces"]}
if date not in plan:
    print(json.dumps({"error": f"No hay paquete para {date}"})); sys.exit(2)

d = dt.date.fromisoformat(date)
nice = f"{DIAS[d.weekday()]} {d.day} {MESES[d.month - 1]}"
repo = cfg["repo"]
base = f"https://github.com/{repo}/raw/media/dias/{date}"
readme = f"https://github.com/{repo}/blob/main/dias/{date}/README.md"
auto = next((r["times"] for r in cfg["auto_metricool"] if r["from"] <= date <= r["to"]), [])
yt = cfg.get("youtube_time", "19:00") if (d.day <= cfg.get("youtube_max_day", 10) or (d.year == 2026 and d.month == 10)) else None
slots = plan[date]

subject = f"🎬 TikTok + Instagram hoy {nice}: {len(slots)} piezas"
H = lambda s: html.escape(s)
pre = "white-space:pre-wrap;background:#f4f6f9;border:1px solid #dde3ea;border-radius:8px;padding:12px;font:14px/1.45 -apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:6px 0 14px"
rows, blocks, text = [], [], [subject, "", f"Descarga todo (.zip): {base}/{date}.zip", f"Copys en la web: {readme}", ""]
for i, s in enumerate(slots, 1):
    p = pool[s["piece"]]; b = render.CAT["books"][p["book"]]
    f = f"{i:02d}_{s['time'].replace(':', 'h')}_{p['book']}.mp4"
    hook = p.get("hook") or p["slides"][0]["h"]
    fmt = "Reel" if p["fmt"] == "reel" else "Carrusel (video)"
    tk, ig = render.caption(p), render.caption_ig(p)
    rows.append(f"<tr><td style='padding:6px 10px'><b>{s['time']}</b></td><td style='padding:6px 10px'>{H(hook)}<br>"
                f"<span style='color:#667'>{H(b['title'])} · {fmt}</span></td>"
                f"<td style='padding:6px 10px'><a href='{base}/{f}'>⬇️ video</a></td></tr>")
    blocks.append(f"<h3 style='margin:22px 0 4px'>{i}. {s['time']} — {H(hook)}</h3>"
                  f"<div><a href='{base}/{f}'>⬇️ Descargar video</a></div>"
                  f"<div style='margin-top:8px'><b>TikTok</b> (activa <i>Contenido comercial › Tu marca</i>)</div><div style='{pre}'>{H(tk)}</div>"
                  f"<div><b>Instagram Reels</b></div><div style='{pre}'>{H(ig)}</div>")
    text += [f"{i}) {s['time']} · {hook} — {fmt}", f"   Video: {base}/{f}", "   --- TikTok ---", tk, "   --- Instagram ---", ig, ""]

auto_line = []
if auto: auto_line.append(f"TikTok {', '.join(auto)} (Metricool)")
if yt: auto_line.append(f"YouTube Short {yt}")
auto_html = (f"<p style='color:#556'>✅ Automático hoy, no hagas nada: {' · '.join(auto_line)}.</p>" if auto_line else "")
html_body = f"""<div style="font:15px/1.5 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1b2430;max-width:640px">
<h2 style="margin:0 0 6px">{H(subject)}</h2>
<p style="margin:0 0 12px">Mismo video en TikTok (@zone_digital25) e Instagram (@zone-digital25). Prográmalos a su hora en un solo bloque (≈10 min).</p>
<p><a href="{base}/{date}.zip" style="background:#111827;color:#fff;padding:10px 16px;border-radius:8px;text-decoration:none">⬇️ Descargar todo (.zip)</a>
&nbsp; <a href="{readme}">Ver copys en la web</a></p>
<table style="border-collapse:collapse;border:1px solid #dde3ea;margin:10px 0">{''.join(rows)}</table>
{auto_html}
{''.join(blocks)}
<p style="color:#778;font-size:13px;margin-top:24px">Paso a paso — TikTok: + › Subir › video › pega el copy › Más opciones › Contenido comercial › Tu marca › Programar. Instagram: + › Reel › mismo video › pega el copy › Compartir (o Meta Business Suite).</p>
</div>"""
if auto_line: text.insert(4, "Automático hoy: " + " · ".join(auto_line))
print(json.dumps({"subject": subject, "html": html_body, "text": "\n".join(text)}, ensure_ascii=False))

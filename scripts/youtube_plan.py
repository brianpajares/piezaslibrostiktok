#!/usr/bin/env python3
"""Lista los Shorts de YouTube a programar en Metricool (plan gratis: 20/mes) para un rango de fechas.

  python3 scripts/youtube_plan.py --from 2026-10-29 --to 2026-11-04

Regla: un Short al día a las config.youtube_time (19:00 Lima) en los días 1–config.youtube_max_day (10) de cada mes
(y del 29 al 31 de octubre de 2026). Usa el primer REEL del paquete manual del día (o la primera pieza).
Omite los días ya registrados en content/youtube.json. Imprime JSON: [{date, piece, url, payload}].
Después de programar cada uno en Metricool, regístralo: --mark FECHA METRICOOL_ID
"""
import argparse, datetime as dt, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
os.environ.setdefault("ZP_OUT", os.path.join(ROOT, "build", "_render"))
import render  # noqa: E402

CFG = json.load(open(os.path.join(ROOT, "content", "config.json"), encoding="utf-8"))
YT_F = os.path.join(ROOT, "content", "youtube.json")
YT_TIME = CFG.get("youtube_time", "19:00")


def is_yt_day(date):
    d = dt.date.fromisoformat(date)
    return date >= "2026-10-29" and (d.day <= CFG.get("youtube_max_day", 10) or (d.year == 2026 and d.month == 10))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="a"); ap.add_argument("--to", dest="b")
    ap.add_argument("--mark", nargs=2, metavar=("FECHA", "ID"))
    a = ap.parse_args()
    done = json.load(open(YT_F, encoding="utf-8")) if os.path.exists(YT_F) else {}
    if a.mark:
        done[a.mark[0]] = a.mark[1]
        json.dump(done, open(YT_F, "w", encoding="utf-8"), indent=1, sort_keys=True)
        print("ok", a.mark[0]); return
    plan = json.load(open(os.path.join(ROOT, "content", "plan.json"), encoding="utf-8"))
    pool = {p["id"]: p for p in json.load(open(os.path.join(ROOT, "content", "pool.json"), encoding="utf-8"))["pieces"]}
    d0, d1 = dt.date.fromisoformat(a.a), dt.date.fromisoformat(a.b)
    out = []
    for k in range((d1 - d0).days + 1):
        date = str(d0 + dt.timedelta(days=k))
        if not is_yt_day(date) or date in done or date not in plan:
            continue
        slots = plan[date]
        idx = next((i for i, s in enumerate(slots) if pool[s["piece"]]["fmt"] == "reel"), 0)
        s = slots[idx]; p = pool[s["piece"]]
        f = f"{idx + 1:02d}_{s['time'].replace(':', 'h')}_{p['book']}.mp4"
        url = f"https://raw.githubusercontent.com/{CFG['repo']}/media/dias/{date}/{f}"
        title, desc = render.caption_yt(p)
        b = render.CAT["books"][p["book"]]
        payload = {
            "autoPublish": True, "descendants": [], "draft": False, "firstCommentText": "", "hasNotReadNotes": False,
            "media": [url], "mediaAltText": [], "providers": [{"network": "youtube"}],
            "publicationDate": {"dateTime": f"{date}T{YT_TIME}:00", "timezone": "America/Lima"},
            "shortener": False, "smartLinkData": {"ids": []}, "text": desc,
            "youtubeData": {"title": title, "type": "short", "privacy": "public", "madeForKids": False,
                            "category": "EDUCATION", "isAiGeneratedContent": False,
                            "tags": [t.lstrip("#") for t in b["tags"].split()[:5]] + ["zonedigital", "books"]},
        }
        out.append({"date": date, "piece": p["id"], "url": url, "datetime": f"{date}T{YT_TIME}:00-05:00", "payload": payload})
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

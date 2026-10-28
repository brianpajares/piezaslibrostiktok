#!/usr/bin/env python3
"""Zone Digital promo engine — renders 9:16 reels (MP4) and 4:5 carousels (PNG)
from catalog.json + calendar.json.

Usage:
  python3 render.py                 # render every post in calendar.json
  python3 render.py --days 1 2 3    # render specific days
  python3 render.py --jobs 4        # parallel workers

Real covers: drop <KINDLE_ASIN>.jpg (or .png) into ./covers/ and the engine uses it
instead of the generated cover.
"""
import argparse, json, math, os, subprocess, wave
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("ZP_OUT", os.path.join(ROOT, "out"))
COVERS = os.path.join(ROOT, "covers")
CAT = json.load(open(os.path.join(ROOT, "catalog.json"), encoding="utf-8"))
_cal = os.path.join(ROOT, "calendar.json")
CAL = json.load(open(_cal, encoding="utf-8")) if os.path.exists(_cal) else {"start": None, "time": None, "posts": []}

BG1, BG2 = (11, 14, 20), (4, 6, 11)
WHITE, MUTED, PANEL = (244, 246, 250), (150, 160, 178), (20, 25, 36)
FPS = 30

# ---------- fonts ----------
_LOCAL_FONTS = os.path.join(ROOT, "fonts")
FD = _LOCAL_FONTS if os.path.isdir(_LOCAL_FONTS) else "/usr/share/fonts/opentype/inter/"
def _f(name, size):
    for n in (name, "Inter-Bold.otf"):
        p = os.path.join(FD, n)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
_FC = {}
def F(weight, size):
    key = (weight, size)
    if key not in _FC:
        name = {"black": "Inter-Black.otf", "bold": "Inter-Bold.otf", "semi": "Inter-SemiBold.otf",
                "med": "Inter-Medium.otf", "reg": "Inter-Regular.otf"}[weight]
        _FC[key] = _f(name, size)
    return _FC[key]

TXT = {
    "es": {"bio": "LINK EN LA BIO", "search": "o búscalo en Amazon:", "kindle": "Kindle · USD 9.99",
           "paper": "También en tapa blanda", "swipe": "DESLIZA", "keys": "CLAVES", "save": "Guárdalo para después"},
    "en": {"bio": "LINK IN BIO", "search": "or search on Amazon:", "kindle": "Kindle · USD 9.99",
           "paper": "Also in paperback", "swipe": "SWIPE", "keys": "KEYS", "save": "Save it for later"},
}

# ---------- helpers ----------
def wrap(text, font, maxw):
    out = []
    for para in text.split("\n"):
        words, line = para.split(), ""
        for w in words:
            t = (line + " " + w).strip()
            if font.getlength(t) <= maxw or not line:
                line = t
            else:
                out.append(line); line = w
        out.append(line)
    return out

def fit_lines(text, weight, size, maxw, maxlines, minsize=40):
    while size > minsize:
        lines = wrap(text, F(weight, size), maxw)
        if len(lines) <= maxlines:
            return lines, size
        size -= 4
    return wrap(text, F(weight, size), maxw), size

def text_block(lines, font, fill, lh, align="center", width=None):
    width = width or int(max(font.getlength(l) for l in lines)) + 8
    h = int(lh * len(lines)) + 16
    im = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        x = (width - font.getlength(l)) / 2 if align == "center" else 0
        d.text((x, i * lh), l, font=font, fill=fill)
    return im

def with_alpha(im, a):
    if a >= 0.999: return im
    if a <= 0.001: return None
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return im

def paste(base, im, x, y, a=1.0):
    im = with_alpha(im, a)
    if im is not None:
        base.alpha_composite(im, (int(x), int(y)))

def ease(t): t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3
def back(t):
    t = max(0.0, min(1.0, t)); c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2
def ramp(t, a, b): return max(0.0, min(1.0, (t - a) / (b - a)))

def gradient(w, h):
    y = np.linspace(0, 1, h)[:, None]
    col = np.array(BG1) * (1 - y) + np.array(BG2) * y          # (h, 3)
    arr = np.repeat(col[:, None, :], w, axis=1)                  # (h, w, 3)
    return Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")

def glow(size, color, alpha=90):
    g = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    d.ellipse((size * .2, size * .2, size * .8, size * .8), fill=color + (alpha,))
    return g.filter(ImageFilter.GaussianBlur(size * .14))

def dot_grid(w, h, step=54, a=26):
    g = Image.new("RGBA", (w, h + step), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    for yy in range(0, h + step, step):
        for xx in range(step // 2, w, step):
            d.ellipse((xx - 2, yy - 2, xx + 2, yy + 2), fill=(255, 255, 255, a))
    return g

def logo(size, color):
    """Tech symbol: hexagon with a central node and three circuit spokes."""
    s = size; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = s / 2; r = s * 0.44
    pts = [(c + r * math.cos(math.radians(60 * i - 90)), c + r * math.sin(math.radians(60 * i - 90))) for i in range(6)]
    d.line(pts + [pts[0]], fill=color + (255,), width=max(2, s // 14), joint="curve")
    for i in (0, 2, 4):
        d.line((c, c, pts[i][0] * .55 + c * .45, pts[i][1] * .55 + c * .45), fill=color + (255,), width=max(2, s // 16))
    rr = s * 0.11
    d.ellipse((c - rr, c - rr, c + rr, c + rr), fill=color + (255,))
    return im

EN_LABEL = {"ia": "AI & TECH", "cert": "CERTIFICATION", "neg": "BUSINESS", "min": "MINING", "st": "START UPS"}
def cat_label(b):
    return EN_LABEL[b["cat"]] if b["lang"] == "en" else CAT["cats"][b["cat"]]["label"]

def brand_bar(w, color, label):
    im = Image.new("RGBA", (w, 90), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    im.alpha_composite(logo(56, color), (0, 17))
    d.text((72, 26), "ZONE DIGITAL", font=F("bold", 32), fill=WHITE)
    f = F("bold", 24); tw = f.getlength(label)
    d.rounded_rectangle((w - tw - 44, 22, w, 68), radius=23, outline=color + (255,), width=3)
    d.text((w - tw - 22, 30), label, font=f, fill=color)
    return im

def pill(text, font, fg, bg, padx=40, h=None):
    tw = font.getlength(text); h = h or int(font.size * 2.1)
    im = Image.new("RGBA", (int(tw + padx * 2), h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, h - 1), radius=h // 2, fill=bg)
    d.text((padx, (h - font.size * 1.2) / 2), text, font=font, fill=fg)
    return im

# ---------- book mockup ----------
def make_cover(b, cw=560):
    ch = int(cw * 1.5)
    asin = b["kindle"]
    for ext in (".jpg", ".png", ".jpeg", ".webp"):
        p = os.path.join(COVERS, asin + ext)
        if os.path.exists(p):
            return Image.open(p).convert("RGBA").resize((cw, ch), Image.LANCZOS)
    color = tuple(CAT["cats"][b["cat"]]["color"])
    cov = gradient(cw, ch)
    ov = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for i in range(-ch, cw, 46):
        d.line((i, ch, i + ch, 0), fill=color + (18,), width=2)
    cov.alpha_composite(ov)
    cov.alpha_composite(glow(int(cw * 1.3), color, 70), (int(cw * .05), int(ch * .35)))
    d = ImageDraw.Draw(cov)
    d.rectangle((0, 0, cw, 14), fill=color)
    d.text((44, 52), cat_label(b), font=F("bold", 22), fill=color)
    lines, sz = fit_lines(b["title"].upper() if len(b["title"]) < 26 else b["title"], "black", 64, cw - 88, 5, 34)
    y = 110
    for l in lines:
        d.text((44, y), l, font=F("black", sz), fill=WHITE); y += int(sz * 1.12)
    d.rectangle((44, y + 18, 150, y + 26), fill=color)
    sl, _ = fit_lines(b["sub"], "med", 26, cw - 88, 4, 20)
    y += 52
    for l in sl:
        d.text((44, y), l, font=F("med", 26), fill=(200, 208, 222)); y += 36
    cov.alpha_composite(logo(40, color), (44, ch - 78))
    d.text((96, ch - 70), "ZONE DIGITAL", font=F("bold", 24), fill=WHITE)
    return cov

def make_book(b, cw=560):
    cov = make_cover(b, cw); ch = cov.height
    sp, pad = 26, 70
    W, H = cw + sp + 14 + pad * 2, ch + pad * 2 + 30
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
    ds.rounded_rectangle((pad + 20, pad + 40, pad + sp + cw + 30, pad + ch + 40), radius=12, fill=(0, 0, 0, 200))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(28)))
    d = ImageDraw.Draw(im)
    # pages edge
    d.rectangle((pad + sp + cw - 4, pad + 8, pad + sp + cw + 12, pad + ch - 6), fill=(230, 226, 214))
    for k in range(0, 14, 3):
        d.line((pad + sp + cw + k - 2, pad + 10, pad + sp + cw + k - 2, pad + ch - 8), fill=(190, 186, 176), width=1)
    # spine
    color = tuple(CAT["cats"][b["cat"]]["color"])
    d.rectangle((pad, pad, pad + sp, pad + ch), fill=tuple(int(c * .45) for c in color))
    im.alpha_composite(cov, (pad + sp, pad))
    hl = Image.new("RGBA", (18, ch), (255, 255, 255, 40))
    im.alpha_composite(hl, (pad + sp, pad))
    return im

# ---------- music (original, synthesized) ----------
def music(path, dur, hits=()):
    sr = 44100; n = int(sr * dur); t = np.arange(n) / sr
    bpm = 104; beat = 60 / bpm
    chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
    sig = np.zeros(n)
    bar = beat * 4
    for i in range(int(dur / bar) + 1):
        s, e = int(i * bar * sr), min(n, int((i + 1) * bar * sr))
        if s >= n: break
        tt = t[s:e] - i * bar
        env = np.minimum(1, tt / 0.4) * np.exp(-tt * 0.25)
        for m in chords[i % 4]:
            f = 440 * 2 ** ((m - 69) / 12)
            for hmul, amp in ((1, .5), (2, .18), (3, .07)):
                sig[s:e] += amp * np.sin(2 * np.pi * f * hmul * tt) * env * 0.11
        f0 = 440 * 2 ** ((chords[i % 4][0] - 24 - 69) / 12)
        sig[s:e] += 0.16 * np.sin(2 * np.pi * f0 * tt) * np.exp(-((tt % beat) * 3))
    for k in range(int(dur / beat) + 1):
        s = int(k * beat * sr); L = int(0.18 * sr)
        if s >= n: break
        tt = np.arange(min(L, n - s)) / sr
        sig[s:s + len(tt)] += 0.5 * np.sin(2 * np.pi * (52 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 18)
        hs = int((k * beat + beat / 2) * sr)
        if hs < n:
            hl = min(int(0.04 * sr), n - hs)
            sig[hs:hs + hl] += 0.05 * np.random.randn(hl) * np.exp(-np.arange(hl) / sr * 90)
    for h in hits:
        s = int(max(0, h - 0.45) * sr); L = min(int(0.6 * sr), n - s)
        if L <= 0: continue
        nz = np.random.randn(L); nz = np.convolve(nz, np.ones(6) / 6, "same")
        sig[s:s + L] += 0.12 * nz * np.sin(np.linspace(0, np.pi, L)) ** 2
    sig *= np.minimum(1, t / 0.3) * np.minimum(1, (dur - t) / 0.6)
    sig = sig / (np.abs(sig).max() + 1e-9) * 0.6
    st = np.stack([sig, sig], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((st * 32767).astype(np.int16).tobytes())

# ---------- reel ----------
def render_reel(p):
    b = CAT["books"][p["book"]]; L = TXT[b["lang"]]
    color = tuple(CAT["cats"][b["cat"]]["color"])
    W, H, DUR = 1080, 1920, 15.5
    name = f"day{p['day']:02d}_reel_{p['book']}"
    os.makedirs(OUT, exist_ok=True)
    mp4, wav = os.path.join(OUT, name + ".mp4"), os.path.join(OUT, name + ".wav")
    T1, T2, T3 = 3.4, 9.6, 12.9

    base = gradient(W, H)
    grid = dot_grid(W, H)
    gl = glow(1300, color, 85)
    bar = brand_bar(W - 120, color, cat_label(b))

    hl, hs = fit_lines(p["hook"], "black", 112, W - 150, 5, 70)
    hook_lines = [text_block([l], F("black", hs), WHITE, hs * 1.08) for l in hl]
    hook_h = int(hs * 1.08 * len(hl))

    cards = []
    for i, pt in enumerate(p["points"]):
        cw, chh = W - 140, 210
        c = Image.new("RGBA", (cw, chh), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
        d.rounded_rectangle((0, 0, cw - 1, chh - 1), radius=34, fill=PANEL + (235,), outline=color + (120,), width=2)
        d.ellipse((34, chh / 2 - 46, 126, chh / 2 + 46), fill=color)
        nf = F("black", 50); d.text((80 - nf.getlength(str(i + 1)) / 2, chh / 2 - 31), str(i + 1), font=nf, fill=BG1)
        pl, ps = fit_lines(pt, "bold", 50, cw - 200, 2, 36)
        y0 = chh / 2 - len(pl) * ps * 1.15 / 2
        for k, l in enumerate(pl):
            d.text((160, y0 + k * ps * 1.15), l, font=F("bold", ps), fill=WHITE)
        cards.append(c)
    head = text_block([f"{len(p['points'])} {L['keys']}"], F("bold", 34), color, 40)

    book = make_book(b, 560)
    kindle = pill(L["kindle"], F("bold", 40), BG1, color)
    paper = text_block([L["paper"]], F("med", 32), MUTED, 38) if b.get("paper") else None
    cta = pill(L["bio"], F("black", 64), BG1, color, padx=60)
    search = text_block([L["search"]], F("med", 36), MUTED, 42)
    tl, ts = fit_lines(b["title"], "bold", 46, W - 160, 2, 32)
    ttl = text_block(tl, F("bold", ts), WHITE, ts * 1.15)
    site = text_block([CAT["brand"]["site"]], F("semi", 36), color, 42)

    music(wav, DUR, hits=(T1, T2, T3))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", mp4]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        fr = base.copy()
        off = int((t * 22) % 54)
        fr.alpha_composite(grid.crop((0, off, W, off + H)))
        gx = int(W / 2 - 650 + 160 * math.sin(t * 0.5)); gy = int(560 + 260 * math.sin(t * 0.33))
        fr.alpha_composite(gl, (gx, gy))
        paste(fr, bar, 60, 70)

        # scene 1: hook
        if t < T1 + 0.4:
            out = 1 - ramp(t, T1 - 0.1, T1 + 0.3)
            y0 = (H - hook_h) / 2 - 120
            for i, im in enumerate(hook_lines):
                k = ease(ramp(t, 0.05 + i * 0.12, 0.55 + i * 0.12))
                paste(fr, im, (W - im.width) / 2, y0 + i * hs * 1.08 + (1 - k) * 60 - (1 - out) * 80, k * out)
            ul = ease(ramp(t, 0.6, 1.2)) * out
            if ul > 0:
                d = ImageDraw.Draw(fr); y = y0 + hook_h + 40
                d.rounded_rectangle((W / 2 - 160 * ul, y, W / 2 + 160 * ul, y + 12), radius=6, fill=color)
        # scene 2: points
        if T1 <= t < T2 + 0.4:
            out = 1 - ramp(t, T2 - 0.1, T2 + 0.3)
            paste(fr, head, (W - head.width) / 2, 520 - (1 - ease(ramp(t, T1, T1 + .4))) * 30, ease(ramp(t, T1, T1 + .4)) * out)
            for i, c in enumerate(cards):
                st = T1 + 0.2 + i * 1.6
                k = back(ramp(t, st, st + 0.55))
                a = ramp(t, st, st + 0.3) * out
                paste(fr, c, 70 + (1 - k) * 420, 620 + i * 250, a)
        # scene 3 + 4: book and CTA
        if t >= T2:
            k = back(ramp(t, T2, T2 + 0.7))
            mv = ease(ramp(t, T3, T3 + 0.6))
            bob = 10 * math.sin(t * 2.2)
            scale = 1 - 0.28 * mv
            bk = book if scale > 0.999 else book.resize((int(book.width * scale), int(book.height * scale)), Image.BILINEAR)
            by = 330 + (1 - k) * 900 - mv * 120 + bob
            paste(fr, bk, (W - bk.width) / 2, by, ramp(t, T2, T2 + 0.3))
            a3 = ramp(t, T2 + 0.5, T2 + 0.9) * (1 - mv)
            paste(fr, kindle, (W - kindle.width) / 2, 1430, a3)
            if paper: paste(fr, paper, (W - paper.width) / 2, 1540, a3)
            if t >= T3:
                c = ease(ramp(t, T3 + 0.2, T3 + 0.7))
                pulse = 1 + 0.03 * math.sin((t - T3) * 7)
                ct = cta.resize((int(cta.width * pulse), int(cta.height * pulse)), Image.BILINEAR)
                paste(fr, ct, (W - ct.width) / 2, 1185 + (1 - c) * 60, c)
                c2 = ease(ramp(t, T3 + 0.5, T3 + 1.0))
                paste(fr, search, (W - search.width) / 2, 1360, c2)
                paste(fr, ttl, (W - ttl.width) / 2, 1420, c2)
                paste(fr, site, (W - site.width) / 2, 1440 + ttl.height + 10, c2)
        # progress bar
        d = ImageDraw.Draw(fr)
        d.rectangle((0, H - 10, int(W * t / DUR), H), fill=color)
        ff.stdin.write(fr.convert("RGB").tobytes())
    ff.stdin.close(); ff.wait(); os.remove(wav)
    return mp4

# ---------- carousel ----------
def render_carousel(p):
    b = CAT["books"][p["book"]]; L = TXT[b["lang"]]
    color = tuple(CAT["cats"][b["cat"]]["color"])
    W, H = 1080, 1350
    folder = os.path.join(OUT, f"day{p['day']:02d}_carousel_{p['book']}")
    os.makedirs(folder, exist_ok=True)
    slides = p["slides"]; total = len(slides) + 1
    grid = dot_grid(W, H)
    bar = brand_bar(W - 140, color, cat_label(b))
    files = []

    def frame(i):
        fr = gradient(W, H); fr.alpha_composite(grid.crop((0, 0, W, H)))
        fr.alpha_composite(glow(1200, color, 70), (-60 + (i % 2) * 120, 260 + (i % 3) * 60))
        paste(fr, bar, 70, 60)
        d = ImageDraw.Draw(fr)
        d.rectangle((0, H - 8, int(W * (i + 1) / total), H), fill=color)
        idx = f"{i + 1:02d}/{total:02d}"
        d.text((W - 70 - F("bold", 28).getlength(idx), H - 70), idx, font=F("bold", 28), fill=MUTED)
        return fr, d

    for i, s in enumerate(slides):
        fr, d = frame(i)
        if i == 0:
            hl, hs = fit_lines(s["h"], "black", 104, W - 160, 5, 64)
            y = 330
            for l in hl:
                d.text((80, y), l, font=F("black", hs), fill=WHITE); y += int(hs * 1.08)
            d.rounded_rectangle((80, y + 30, 260, y + 42), radius=6, fill=color)
            bl, bs = fit_lines(s["b"], "med", 40, W - 160, 3, 30)
            y += 90
            for l in bl:
                d.text((80, y), l, font=F("med", bs), fill=(205, 212, 226)); y += int(bs * 1.3)
            sw = pill(L["swipe"] + "  >>", F("black", 34), BG1, color)
            paste(fr, sw, 80, H - 200)
        else:
            d.text((80, 240), f"{i:02d}", font=F("black", 150), fill=color + (255,))
            hl, hs = fit_lines(s["h"], "black", 76, W - 160, 3, 50)
            y = 450
            for l in hl:
                d.text((80, y), l, font=F("black", hs), fill=WHITE); y += int(hs * 1.1)
            y += 40
            opts = "\n" in s["b"]
            if opts:
                for line in s["b"].split("\n"):
                    ol, os_ = fit_lines(line, "bold", 46, W - 230, 2, 32)
                    bh = int(len(ol) * os_ * 1.2) + 44
                    d.rounded_rectangle((80, y, W - 80, y + bh), radius=26, fill=PANEL + (255,), outline=color + (110,), width=2)
                    yy = y + 22
                    for l in ol:
                        d.text((116, yy), l, font=F("bold", os_), fill=WHITE); yy += int(os_ * 1.2)
                    y += bh + 20
            else:
                bl, bs = fit_lines(s["b"], "med", 52, W - 160, 7, 34)
                for l in bl:
                    d.text((80, y), l, font=F("med", bs), fill=(214, 220, 232)); y += int(bs * 1.35)
        fp = os.path.join(folder, f"slide{i + 1:02d}.png"); fr.convert("RGB").save(fp, optimize=True); files.append(fp)

    fr, d = frame(total - 1)
    bk = make_book(b, 400); paste(fr, bk, (W - bk.width) / 2, 140)
    y = 140 + bk.height - 10
    cta = pill(L["bio"], F("black", 56), BG1, color, padx=56); paste(fr, cta, (W - cta.width) / 2, y)
    y += cta.height + 30
    st = text_block([L["search"]], F("med", 34), MUTED, 40); paste(fr, st, (W - st.width) / 2, y); y += 50
    tl, ts = fit_lines(b["title"], "bold", 42, W - 180, 2, 30)
    tt = text_block(tl, F("bold", ts), WHITE, ts * 1.15); paste(fr, tt, (W - tt.width) / 2, y)
    fp = os.path.join(folder, f"slide{total:02d}.png"); fr.convert("RGB").save(fp, optimize=True); files.append(fp)
    return folder

# ---------- captions ----------
def caption(p):
    b = CAT["books"][p["book"]]; es = b["lang"] == "es"
    hook = p.get("hook") or p["slides"][0]["h"]
    fmt = "Kindle USD 9.99" + ((" · Tapa blanda disponible" if es else " · Paperback available") if b.get("paper") else "")
    cta = (f'👉 Link en la bio o busca "{b["title"]}" en Amazon' if es
           else f'👉 Link in bio or search "{b["title"]}" on Amazon')
    extra = "#zonedigital #libros #LATAM #aprendeentiktok" if es else "#zonedigital #books #BookTok #learnontiktok"
    return f"{hook}\n\n{p['cap']}\n\n📘 {b['title']} — {fmt}\n{cta}\n\n{b['tags']} {extra}"

def caption_ig(p):
    """Instagram Reels: same message, link-in-bio CTA, 3-5 hashtags (Instagram's own guidance)."""
    b = CAT["books"][p["book"]]; es = b["lang"] == "es"
    hook = p.get("hook") or p["slides"][0]["h"]
    fmt = "Kindle USD 9.99" + ((" · Tapa blanda" if es else " · Paperback") if b.get("paper") else "")
    cta = ("👉 Link en la bio · o busca el título en Amazon" if es
           else "👉 Link in bio · or search the title on Amazon")
    save = "💾 Guárdalo y compártelo con quien lo necesite." if es else "💾 Save it and share it with someone who needs it."
    tags = " ".join(b["tags"].split()[:4] + ["#zonedigital"])
    return f"{hook}\n\n{p['cap']}\n{save}\n\n📘 {b['title']} — {fmt}\n{cta}\n\n{tags}"

def caption_yt(p):
    """YouTube Shorts: (title ≤100 chars with #Shorts, description)."""
    b = CAT["books"][p["book"]]; es = b["lang"] == "es"
    hook = (p.get("hook") or p["slides"][0]["h"]).strip()
    title = (hook[:88].rstrip() + " #Shorts")
    cta = (f'📘 Libro: {b["title"]} (Kindle USD 9.99) — búscalo en Amazon o entra a zone-digital.com'
           if es else f'📘 Book: {b["title"]} (Kindle USD 9.99) — search it on Amazon or visit zone-digital.com')
    amazon = f"https://www.amazon.com/dp/{b['kindle']}"
    tags = " ".join(b["tags"].split()[:3] + ["#Shorts"])
    desc = f"{hook}\n\n{p['cap']}\n\n{cta}\n{amazon}\n\n{tags}"
    return title, desc

def manifest():
    import datetime as dt
    start = dt.date.fromisoformat(CAL["start"])
    rows = []
    for p in CAL["posts"]:
        b = CAT["books"][p["book"]]
        name = f"day{p['day']:02d}_{p['fmt']}_{p['book']}"
        rows.append({
            "day": p["day"], "date": str(start + dt.timedelta(days=p["day"] - 1)), "fmt": p["fmt"],
            "book": p["book"], "title": b["title"], "lang": b["lang"], "cat": b["cat"],
            "hook": p.get("hook") or p["slides"][0]["h"], "caption": caption(p),
            "amazon": f"https://www.amazon.com/dp/{b['kindle']}",
            "paperback": f"https://www.amazon.com/dp/{b['paper']}" if b.get("paper") else None,
            "page": f"https://zone-digital.com/libros/{b['page']}/",
            "asset": name + (".mp4" if p["fmt"] == "reel" else ""),
            "slides": len(p["slides"]) + 1 if p["fmt"] == "carousel" else 0,
        })
    json.dump({"time": CAL["time"], "posts": rows}, open(os.path.join(OUT, "data.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return rows

# ---------- carousel as 9:16 slideshow video (for TikTok API without verified domain) ----------
def render_carousel_video(p, per=3.2, fade=0.45):
    """Render the carousel slides, then turn them into a 1080x1920 MP4 slideshow with music."""
    b = CAT["books"][p["book"]]
    color = tuple(CAT["cats"][b["cat"]]["color"])
    folder = render_carousel(p)
    slides = sorted(f for f in os.listdir(folder) if f.startswith("slide") and f.endswith(".png"))
    W, H = 1080, 1920
    bg = gradient(W, H); bg.alpha_composite(dot_grid(W, H).crop((0, 0, W, H)))
    bg.alpha_composite(glow(1400, color, 60), (-160, 300))
    frames = []
    for i, s in enumerate(slides):
        fr = bg.copy()
        im = Image.open(os.path.join(folder, s)).convert("RGBA")
        paste(fr, im, 0, (H - im.height) // 2 - 40)
        d = ImageDraw.Draw(fr)
        d.rectangle((0, H - 10, int(W * (i + 1) / len(slides)), H), fill=color)
        fp = os.path.join(folder, f"v{i + 1:02d}.png"); fr.convert("RGB").save(fp); frames.append(fp)
    n = len(frames); dur = n * per - (n - 1) * fade
    mp4 = folder + ".mp4"; wav = folder + ".wav"
    music(wav, dur + 0.2, hits=[k * (per - fade) for k in range(1, n)])
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for f in frames:
        cmd += ["-loop", "1", "-t", f"{per:.2f}", "-framerate", str(FPS), "-i", f]
    cmd += ["-i", wav]
    chain, last = [], "[0:v]"
    for k in range(1, n):
        off = k * (per - fade)
        out = f"[x{k}]"
        chain.append(f"{last}[{k}:v]xfade=transition=slideleft:duration={fade}:offset={off:.2f}{out}")
        last = out
    chain.append(f"{last}format=yuv420p[v]")
    cmd += ["-filter_complex", ";".join(chain), "-map", "[v]", "-map", f"{n}:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", mp4]
    subprocess.run(cmd, check=True)
    os.remove(wav)
    return mp4

def job(p):
    return render_reel(p) if p["fmt"] == "reel" else render_carousel(p)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, nargs="*")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    posts = [p for p in CAL["posts"] if not a.days or p["day"] in a.days]
    manifest()
    with Pool(min(a.jobs, len(posts))) as pool:
        for r in pool.imap_unordered(job, posts):
            print("ok", os.path.relpath(r, ROOT), flush=True)

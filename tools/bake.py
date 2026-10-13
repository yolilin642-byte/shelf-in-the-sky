# 把 photos/ 里的照片烤成页面要用的图，再写出 photos.json。加了、改了照片就再跑一遍（已经烤过的跳过，--all 全部重烤）。
# Bake the photos in photos/ into the images the page uses, and write photos.json. Re-run after adding photos (--all rebuilds everything).
#
#   python tools/bake.py                 按月分段 / group by month
#   python tools/bake.py --group year    按年 / by year
#   python tools/bake.py --group decade  按十年（老照片只知道年份时好用） / by decade
#
# 每张照片可以配一个同名 .txt（photo.jpg → photo.txt），写在照片背面：
#   正文随便写，**粗体** 认得；
#   单独一行「日期：约 1843–1853」/「date: c. 1843」只改背面显示的日期；
#   最后一行「标签：人像 · 海」/「tags: portrait, sea」是标签，左边那列按它挑。
# 日期（决定排在哪一段）依次看：文件名开头的 2024-05-01 / 2024-05 / 1867，照片里的拍摄时间，文件修改时间。
#
# 要装 Pillow 和 numpy：pip install pillow numpy
import sys, os, re, json, math, hashlib, datetime
from PIL import Image, ImageOps, ImageDraw, ImageFilter
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PH, OUT, AS = os.path.join(ROOT, "photos"), os.path.join(ROOT, "baked"), os.path.join(ROOT, "assets")
EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALL = "--all" in sys.argv
def _last_group():
    try: return json.load(open(os.path.join(ROOT, "photos.json"), encoding="utf-8")).get("group") or "month"
    except Exception: return "month"
# 没写 --group 就沿用上一次的（后台自动重烤时也不会把分段改回按月）
GROUP = sys.argv[sys.argv.index("--group") + 1] if "--group" in sys.argv else _last_group()

LONG = 640          # 烤好的那张，照片部分长边多少像素 / long side of the baked photo
BLONG = 360         # 蒙上时用的糊图 / the blurred one used by "veil"
RIM_N, RIM_S = .06, .04   # 相纸边占短边多少：普通照片／细长截图（页面里同一对数） / paper rim: normal / tall slips (same numbers in index.html)
SS = 3              # 毛边超采样 / deckle supersampling

_paper = None
def paper(w, h):
    global _paper
    if _paper is None:
        t = Image.open(os.path.join(AS, "paper.webp")).convert("RGB")
        _paper = t.resize((t.width * 3, t.height * 3), Image.LANCZOS)
    t, c = _paper, Image.new("RGB", (w, h), (248, 243, 232))
    for y in range(0, h, t.height):
        for x in range(0, w, t.width):
            c.paste(t, (x, y))
    return c

def tone(im):
    # 旧相纸的颜色：saturate(.8) sepia(.12) contrast(.93) brightness(1.03)
    a = np.asarray(im, dtype=np.float32) / 255.0
    s = .8
    M1 = np.array([[.213 + .787 * s, .715 - .715 * s, .072 - .072 * s],
                   [.213 - .213 * s, .715 + .285 * s, .072 - .072 * s],
                   [.213 - .213 * s, .715 - .715 * s, .072 + .928 * s]], np.float32)
    k = 1 - .12
    M2 = np.array([[.393 + .607 * k, .769 - .769 * k, .189 - .189 * k],
                   [.349 - .349 * k, .686 + .314 * k, .168 - .168 * k],
                   [.272 - .272 * k, .534 - .534 * k, .131 + .869 * k]], np.float32)
    a = np.clip(a @ M1.T, 0, 1)
    a = np.clip(a @ M2.T, 0, 1)
    a = np.clip(a * .93 + (.5 - .5 * .93), 0, 1)
    a = np.clip(a * 1.03, 0, 1)
    return Image.fromarray((a * 255 + .5).astype(np.uint8), "RGB")

def deckle_pts(w, h, p, a, seed):
    # 毛边：缓缓起伏的圆波，深浅逐个不一样，四角小圆角（跟 index.html 里 deckle() 同一个算法）
    c = max(2.5, p * .45)
    def jit(i):
        v = math.sin((i + 1) * 12.9898 + seed * 78.233) * 43758.5453
        return .78 + .44 * (v - math.floor(v))
    pts, kk = [(c, 0)], [0]
    def bez(p0, p1, p2, p3, n=10):
        for t in [j / n for j in range(1, n + 1)]:
            u = 1 - t
            pts.append((u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                        u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]))
    def edge(x0, y0, x1, y1, nx, ny):
        L = math.hypot(x1 - x0, y1 - y0); tx, ty = (x1 - x0) / L, (y1 - y0) / L
        m = 2 * max(1, round(L / p)); hw = L / m
        P = lambda s, o: (x0 + tx * s + nx * o, y0 + ty * s + ny * o)
        for i in range(m):
            o0 = a * jit(kk[0]) if i % 2 else 0
            o1 = a * jit(kk[0] + 1) if (i + 1) % 2 else 0
            if i % 2: kk[0] += 1
            bez(pts[-1], P(i * hw + hw * .4, o0), P((i + 1) * hw - hw * .4, o1), P((i + 1) * hw, o1))
    def arc(cx, cy, a0, a1, n=8):
        for j in range(1, n + 1):
            t = a0 + (a1 - a0) * j / n
            pts.append((cx + c * math.cos(t), cy + c * math.sin(t)))
    edge(c, 0, w - c, 0, 0, 1);       arc(w - c, c, -math.pi / 2, 0)
    edge(w, c, w, h - c, -1, 0);      arc(w - c, h - c, 0, math.pi / 2)
    edge(w - c, h, c, h, 0, -1);      arc(c, h - c, math.pi / 2, math.pi)
    edge(0, h - c, 0, c, 1, 0);       arc(c, c, math.pi, math.pi * 1.5)
    return pts

def bake(src_im, slip, seed, long_side, blur=False):
    r0 = src_im.width / src_im.height
    pw, ph = (long_side, max(1, round(long_side / r0))) if r0 >= 1 else (max(1, round(long_side * r0)), long_side)
    rp = max(2, round((RIM_S if slip else RIM_N) * min(pw, ph)))
    W, H = pw + 2 * rp, ph + 2 * rp
    photo = tone(src_im.resize((pw, ph), Image.LANCZOS))
    if blur:
        photo = photo.filter(ImageFilter.GaussianBlur(min(pw, ph) * .11))
    can = paper(W, H)
    can.paste(photo, (rp, rp))
    d = ImageDraw.Draw(can, "RGBA")
    lw = max(1, round(min(pw, ph) / 300))
    d.rectangle([rp - lw, rp - lw, rp + pw - 1 + lw, rp + ph - 1 + lw], outline=(70, 60, 40, 56), width=lw)
    if slip:
        # 细长的（手机截图之类）不套毛边：裁齐的白纸片，边上一道细线
        d.rectangle([0, 0, W - 1, H - 1], outline=(112, 94, 66, 90), width=max(1, round(min(pw, ph) / 200)))
        return can.convert("RGBA")
    can = can.convert("RGBA")
    p = (pw + ph) / 34
    a = (pw + ph) * 1.9 / 300
    pts = deckle_pts(W * SS, H * SS, p * SS, a * SS, seed)
    m = Image.new("L", (W * SS, H * SS), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    rim = Image.new("L", (W * SS, H * SS), 0)
    ImageDraw.Draw(rim).line(pts + [pts[0]], fill=255, width=max(SS, round(max(.8, a * .38) * SS)))
    m = m.resize((W, H), Image.LANCZOS)
    rim = rim.resize((W, H), Image.LANCZOS)
    ra = np.asarray(rim, np.float32)[..., None] / 255.0 * .42
    px = np.asarray(can, np.float32)
    px[..., :3] = px[..., :3] * (1 - ra) + np.array([112, 94, 66], np.float32) * ra
    px[..., 3] = np.asarray(m, np.float32)
    return Image.fromarray(px.clip(0, 255).astype(np.uint8), "RGBA")

def read_note(path):
    cap, tags, date = "", [], ""
    if os.path.exists(path):
        lines = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n").strip().split("\n")
        if lines and re.match(r"^\s*(标签|tags?)\s*[:：]", lines[-1], re.I):
            tags = [t.strip() for t in re.split(r"[·,，、/]", re.split(r"[:：]", lines.pop(), 1)[1]) if t.strip()]
        keep = []
        for ln in lines:
            m = re.match(r"^\s*(日期|date)\s*[:：]\s*(.+)$", ln, re.I)
            if m and not date: date = m.group(2).strip()
            else: keep.append(ln)
        cap = "\n".join(keep).strip()
    return cap, tags, date

def day_of(f, im, src):
    m = re.match(r"^(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?(?=[_\s.-]|$)", f)
    if m:
        y, mo, d = m.group(1), m.group(2), m.group(3)
        return y + (f"-{int(mo):02d}" if mo else "") + (f"-{int(d):02d}" if mo and d else "")
    try:
        ex = im.getexif().get_ifd(0x8769).get(36867) or im.getexif().get(306)
        if ex: return ex[:10].replace(":", "-")
    except Exception:
        pass
    return datetime.date.fromtimestamp(os.path.getmtime(src)).isoformat()

os.makedirs(OUT, exist_ok=True)
items = []
for f in sorted(os.listdir(PH)):
    if os.path.splitext(f)[1].lower() not in EXT:
        continue
    src, base = os.path.join(PH, f), os.path.splitext(f)[0]
    dt, dd, db = (os.path.join(OUT, k + "-" + base + ".webp") for k in ("t", "d", "b"))
    raw = Image.open(src)
    im = ImageOps.exif_transpose(raw).convert("RGB")
    if ALL or not (os.path.exists(dt) and os.path.exists(dd) and os.path.exists(db)):
        t = im.copy(); t.thumbnail((400, 400), Image.LANCZOS)
        t.save(dt, "WEBP", quality=80, method=6)
        slip = t.width / t.height < .6
        fit = ImageOps.fit(im, (max(1, round(1000 * t.width / t.height)), 1000) if t.width < t.height else (1000, max(1, round(1000 * t.height / t.width))), Image.LANCZOS)
        seed = int(hashlib.md5(base.encode("utf-8")).hexdigest()[:6], 16) % 997
        bake(fit, slip, seed, LONG).save(dd, "WEBP", quality=82, method=6)
        bake(fit, slip, seed, BLONG, blur=True).save(db, "WEBP", quality=70, method=6)
        print("烤好", f)
    tw, th = Image.open(dt).size
    cap, tags, date = read_note(os.path.join(PH, base + ".txt"))
    it = {"file": f, "day": day_of(f, raw, src), "caption": cap, "tags": tags, "w": tw, "h": th}
    if date: it["date"] = date
    items.append(it)

items.sort(key=lambda x: (x["day"], x["file"]), reverse=True)
json.dump({"group": GROUP, "photos": items}, open(os.path.join(ROOT, "photos.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(items), "张 →", "photos.json", "（按", {"month": "月", "year": "年", "decade": "十年"}.get(GROUP, GROUP), "分段）")

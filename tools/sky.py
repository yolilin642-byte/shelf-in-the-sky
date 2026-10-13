# 换天：把一张图做成页面背后那片天。雾里飘的云团从同一张图上裁，底色、字和字边那圈光晕也照着它配。
# Swap the sky: turn any picture into the sky behind the page. The mist clouds are cut from the same picture,
# and the background tint, text and text halo follow its colours.
#
#   python tools/sky.py my-sky.jpg                         换成这张 / use this picture
#   python tools/sky.py my-sky.jpg --credit "Turner, 1839" 页面最底下那行小字写谁的天 / who painted it (bottom line of the page)
#   python tools/sky.py my-sky.jpg --name sea              起个名字，默认用文件名 / a name; defaults to the file name
#   python tools/sky.py my-sky.jpg --top 0.5               只要画的上半截 / keep only the top half of the picture
#   python tools/sky.py --list                             换过哪些 / the skies you've made
#   python tools/sky.py --use sea                          换回做过的某一片 / switch to one you've made
#   python tools/sky.py --default                          换回 Constable / back to Constable
#
# 做好的放在 assets/skies/<名字>/，assets/sky.json 记着现在用的是哪片。
# 挑几乎全是天的图最好：整张图从上到下都会铺在照片背后，画的下半截要是有人、有房子、有海，底下那排按钮就压在上面看不清，
# 这时加 --top 0.5 之类，只留上面那截天。横的图也比竖的好：页面把它左右镜像接成一圈，太窄的转一圈会重复好几回。
# Pick a picture that is mostly sky: all of it, top to bottom, sits behind the photos, and people or houses in the lower half
# end up under the buttons. Use --top 0.5 (or so) to keep only the sky. Wide beats tall: the page mirrors it into a full circle.
# 天太暗（夜空之类）会自动换成浅色的字、深色的光晕；不满意就改 assets/sky.json 里 css 那几项。
#
# 要装 Pillow 和 numpy：pip install pillow numpy
import sys, os, re, json, time, argparse
from PIL import Image, ImageFilter
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AS = os.path.join(ROOT, "assets")
SKIES, CFG = os.path.join(AS, "skies"), os.path.join(AS, "sky.json")
SKY_H, SKY_W = 1500, 1750   # 页面最多用天的 1750 像素宽 / the page uses at most 1750 px of the sky's width
WISP_W = 620
WISP_AR = [.62, .62, .5, .55, .61, .55]   # 六团云各自的高宽比 / height:width of the six clouds
DEFAULT = {"dir": "", "credit": "John Constable, Cloud Study, 1821", "css": {}}

def hexc(c): return "#%02x%02x%02x" % tuple(int(round(v)) for v in c)
def rgbs(c): return ",".join(str(int(round(v))) for v in c)
def mix(a, b, t): return [x + (y - x) * t for x, y in zip(a, b)]

def palette(sky):
    a = np.asarray(sky.resize((96, max(1, round(96 * sky.height / sky.width)))), np.float32)
    base = a.reshape(-1, 3).mean(0).tolist()
    lum = (.2126 * base[0] + .7152 * base[1] + .0722 * base[2]) / 255
    W, K = [255] * 3, [0] * 3
    if lum >= .45:   # 亮的天：往白里提，跟 Constable 那片手调的配法对得上 / a light sky: lifted towards white, matching the hand-tuned Constable values
        return False, {"base": hexc(mix(base, W, .4)), "veil": hexc(mix(base, W, .65)), "tint": rgbs(mix(base, W, .4)), "glow": rgbs(mix(base, W, .62))}
    return True, {"base": hexc(base), "veil": hexc(mix(base, K, .4)), "tint": rgbs(base), "glow": rgbs(mix(base, K, .55)),
                  "ink": "#ecebe4", "ink2": "#f2f0e8", "soft": "#c9c7bd", "mute": "#dddbd1", "line": "236,234,226", "hl": "14,16,26"}

def spots(L, pw, ph, n):
    # 挑亮的、有纹理的几块，暗东西（树、房子）多的扣分，彼此别叠太多
    # bright, textured patches; ones with a lot of dark stuff (trees, roofs) lose points; not overlapping much
    H, W = L.shape
    D = (L < np.percentile(L, 30)).astype(np.float64)
    I = lambda A: np.pad(A, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    S, S2, SD = I(L.astype(np.float64)), I(L.astype(np.float64) ** 2), I(D)
    box = lambda T, x, y: T[y + ph, x + pw] - T[y, x + pw] - T[y + ph, x] + T[y, x]
    sx, sy, c = max(1, (W - pw) // 40), max(1, (H - ph) // 40), []
    for y in range(0, H - ph + 1, sy):
        for x in range(0, W - pw + 1, sx):
            area = pw * ph
            m = box(S, x, y) / area
            v = max(0.0, box(S2, x, y) / area - m * m)
            c.append((m + .8 * v ** .5 - 1.5 * box(SD, x, y) / area, x, y))
    c.sort(reverse=True)
    for lim in (.15, .35, .6, 1.01):
        out = []
        for _, x, y in c:
            ov = max((max(0, min(x, ox) + pw - max(x, ox)) * max(0, min(y, oy) + ph - max(y, oy))) / (pw * ph) for ox, oy in out) if out else 0
            if ov <= lim: out.append((x, y))
            if len(out) == n: return out
    return (out * n)[:n]

def wisp(patch, ar):
    w = WISP_W
    h = round(w * ar)
    p = patch.resize((w, h), Image.LANCZOS)
    a = np.asarray(p, np.float32) / 255
    L = a @ np.array([.2126, .7152, .0722], np.float32)
    lo, hi = np.percentile(L, 20), np.percentile(L, 98)
    k = np.clip((L - lo) / (hi - lo + 1e-3), 0, 1) ** .9
    k = np.asarray(Image.fromarray((k * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((xx - (w - 1) / 2) / (w / 2), (yy - (h - 1) / 2) / (h / 2))
    e = np.clip((1 - r) / .6, 0, 1)
    e = e * e * (3 - 2 * e)
    al = (250 * e * (.1 + .9 * k ** 1.2)).astype(np.uint8)   # 暗处几乎透明，不把树、房子裁成云 / dark parts stay almost clear, so trees and roofs don't become clouds
    out = p.convert("RGBA")
    out.putalpha(Image.fromarray(al))
    return out

def make(src, name, credit, top=1.0):
    im = Image.open(src)
    im.load()
    im = im.convert("RGB")
    if top < 1: im = im.crop((0, 0, im.width, max(1, round(im.height * top))))
    if im.height < 900: print("  这张图有点矮（%d 像素高），天会糊 / a bit small (%d px tall), the sky will look soft" % (im.height, im.height))
    sky = im.resize((max(1, round(im.width * SKY_H / im.height)), SKY_H), Image.LANCZOS)
    if sky.width > SKY_W:
        x0 = (sky.width - SKY_W) // 2
        sky = sky.crop((x0, 0, x0 + SKY_W, SKY_H))
    if sky.width < sky.height * .9: print("  这张图是竖的，转一圈会重复好几回 / a tall picture repeats several times around the circle")
    d = os.path.join(SKIES, name)
    os.makedirs(d, exist_ok=True)
    sky.save(os.path.join(d, "sky.webp"), quality=80, method=4)
    L = np.asarray(sky.convert("L"), np.float32) / 255
    pw = round(sky.width * .3)
    for q, (x, y) in enumerate(spots(L, pw, round(pw * .62), len(WISP_AR))):
        ph = round(pw * WISP_AR[q])
        y = min(max(0, y + (round(pw * .62) - ph) // 2), sky.height - ph)
        wisp(sky.crop((x, y, x + pw, y + ph)), WISP_AR[q]).save(os.path.join(d, "wisp%d.webp" % q), quality=80, method=4)
    dark, css = palette(sky)
    cfg = {"dir": "skies/%s/" % name, "v": int(time.time()), "credit": credit, "css": css}   # v：同名重做时让浏览器别拿旧图 / so a remade sky isn't served from cache
    json.dump(cfg, open(os.path.join(d, "sky.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return cfg, dark

def use(cfg):
    json.dump(cfg, open(CFG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def main():
    ap = argparse.ArgumentParser(description="换天 / swap the sky")
    ap.add_argument("image", nargs="?")
    ap.add_argument("--name")
    ap.add_argument("--credit")
    ap.add_argument("--top", type=float, default=1.0)
    ap.add_argument("--use")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--default", action="store_true")
    a = ap.parse_args()
    if a.default:
        use(DEFAULT); print("换回 Constable 了 / back to Constable"); return
    if a.list:
        cur = json.load(open(CFG, encoding="utf-8")).get("dir", "") if os.path.exists(CFG) else ""
        print(("* " if not cur else "  ") + "(default) " + DEFAULT["credit"])
        for n in sorted(os.listdir(SKIES)) if os.path.isdir(SKIES) else []:
            f = os.path.join(SKIES, n, "sky.json")
            if os.path.exists(f):
                c = json.load(open(f, encoding="utf-8"))
                print(("* " if c["dir"] == cur else "  ") + n + "  " + c.get("credit", ""))
        return
    if a.use:
        f = os.path.join(SKIES, a.use, "sky.json")
        if not os.path.exists(f): sys.exit("没有叫 %s 的天，先 --list 看看 / no sky called %s, try --list" % (a.use, a.use))
        use(json.load(open(f, encoding="utf-8"))); print("换成 %s 了 / now using %s" % (a.use, a.use)); return
    if not a.image: ap.print_help(); return
    name = a.name or os.path.splitext(os.path.basename(a.image))[0]
    name = re.sub(r"[^a-z0-9_-]+", "-", name.lower()).strip("-") or "sky"
    if not 0.1 <= a.top <= 1: sys.exit("--top 写 0.1 到 1 之间 / --top takes 0.1 to 1")
    cfg, dark = make(a.image, name, a.credit or os.path.splitext(os.path.basename(a.image))[0], a.top)
    use(cfg)
    print("换好了 / done：assets/skies/%s/" % name + ("（暗的天，字换成浅色 / dark sky: light text）" if dark else ""))
    print("刷新页面就能看见。换回来：python tools/sky.py --default / refresh the page; to go back: --default")

if __name__ == "__main__":
    main()

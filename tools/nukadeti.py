#!/usr/bin/env python3
"""nukadeti.py <url> <dir> ["Title"] [--numbered]

Grabs audio from nukadeti.ru into Lantern packages. The page decides the shape:
  * a LISTING (tiles linking to other tale pages)  -> <dir> is a collection; each tile is grabbed
    recursively into <dir>/<slug>/ (or <dir>/NN-<slug>/ with --numbered, keeping the site's order)
  * a MULTI-PART page (player JSON with several files) -> <dir> is a collection of NN-<slug>/ leaves,
    one per part, in order; all parts share the page's cover
  * a SINGLE-file page -> <dir> is one audio leaf
Existing mp3s/covers are skipped, so reruns are incremental. mp3 comes from the site's
download/audio/<id>?h=<hash>&type=<t> endpoint (from the player's data-files JSON); the cover is the
tale's first illustration, else its 400x400 tile, else og:image — square-cropped to 768px."""
import html, io, json, pathlib, re, sys, time, urllib.parse, urllib.request
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"}
BASE = "https://nukadeti.ru"
NUMBERED = "--numbered" in sys.argv

def get(url, referer=None):
    h = dict(UA)
    if referer: h["Referer"] = referer
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=180).read()

def page(url):
    s = get(url).decode("utf-8", "replace")
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
    title = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip() if h1 else url
    title = re.sub(r"^(Аудио ?(сказка|книга|рассказ|рассказы|сказки)|Аудиокнига|Аудиосказки?|Аудиорассказы)\s+", "", title)
    m = re.search(r"data-files='(\[.*?\])'", s)
    files = json.loads(html.unescape(m.group(1))) if m else []
    seen, subs = {}, []
    for mm in re.finditer(r'<a[^>]+href="(/audioskazki/[^"#?]+)"[^>]*>(.*?)</a>', s, re.S):
        href, text = mm.group(1), html.unescape(re.sub(r"<[^>]+>", "", mm.group(2))).strip()
        seen.setdefault(href, set()).add(bool(text))
        if text and href not in [o[0] for o in subs]: subs.append((href, text))
    subs = [(h, t) for h, t in subs if seen[h] == {True, False}]
    img = (re.search(r'href="(/content/images/essence/tale/\d+/\d+\.jpg)"', s)
           or (files and re.search(rf'"(/content/images/static/tale400x400/{files[0].get("ei")}_\d+\.jpg)"', s))
           or re.search(r'"(/content/images/static/tale400x400/\d+_\d+\.jpg)"', s)
           or re.search(r'og:image" content="([^"]+)"', s))
    return title, files, subs, (urllib.parse.urljoin(BASE, img.group(1)) if img else None)

def slug_of(href):
    s = href.rstrip("/").rsplit("/", 1)[-1].replace("_", "-")
    for p in ("nikolaj-nosov-", "nosov-", "dragunskij-", "uspenskij-", "andersen-", "lindgren-"):
        if s.startswith(p): s = s[len(p):]
    return s

def slugify(text, fallback):
    tr = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", ["a","b","v","g","d","e","yo","zh","z","i","j","k","l","m","n","o","p","r","s","t","u","f","h","c","ch","sh","sch","","y","","e","yu","ya"]))
    s = "".join(tr.get(c, c) for c in text.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:40].rstrip("-") or fallback

def cover(url, dst):
    if dst.exists() or not url: return
    try:
        im = Image.open(io.BytesIO(get(url))).convert("RGB")
        w, h = im.size; s = min(w, h)
        im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)).resize((768, 768), Image.LANCZOS).save(dst, quality=88, optimize=True)
    except Exception as e: print("  cover failed:", dst, e)

def yaml_str(s): return json.dumps(s, ensure_ascii=False)

def leaf(d, f, title, url, img):
    d.mkdir(parents=True, exist_ok=True)
    mp3 = d / (slugify(title, "audio") + ".mp3")
    if not mp3.exists() and not list(d.glob("*.mp3")):
        data = get(f"{BASE}/download/audio/{f['i']}?h={f['h']}&type={f['t']}", referer=url)
        if data[:3] != b"ID3" and data[:2] not in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
            print("  NOT MP3:", title, data[:30]); return
        mp3.write_bytes(data)
        (d / "node.yaml").write_text(f"type: audio\ntitle: {yaml_str(title)}\nfile: {mp3.name}\nsource: {url}\n")
        print(f"  ok {d.name}: {title} {f.get('duration')} {len(data)//1024} KB"); time.sleep(1)
    cover(img, d / "cover.jpg")

def collection(d, title, url, img):
    d.mkdir(parents=True, exist_ok=True)
    if not (d / "node.yaml").exists():
        (d / "node.yaml").write_text(f"type: collection\ntitle: {yaml_str(title)}\nsource: {url}\n")
    cover(img, d / "cover.jpg")

def grab(url, d, title=None, depth=0):
    ptitle, files, subs, img = page(url)
    title = title or ptitle
    if subs and depth < 2:
        print(f"{'  '*depth}listing {title}: {len(subs)} items -> {d}")
        collection(d, title, url, img)
        for i, (href, text) in enumerate(subs, 1):
            name = (f"{i:02d}-" if NUMBERED else "") + slug_of(href)
            grab(BASE + href, d / name, None, depth + 1)
    elif len(files) > 1:
        print(f"{'  '*depth}multi-part {title}: {len(files)} parts -> {d}")
        collection(d, title, url, img)
        for i, f in enumerate(files, 1):
            leaf(d / f"{i:02d}-{slugify(f.get('title') or str(i), str(i))}", f, f.get("title") or f"{title} {i}", url, img)
    elif files:
        leaf(d, files[0], title, url, img)
    else:
        print(f"{'  '*depth}NO AUDIO at {url}")
    # collection cover fallback: first child's cover
    if d.is_dir() and not (d / "cover.jpg").exists():
        for c in sorted(d.iterdir()):
            if (c / "cover.jpg").exists(): (d / "cover.jpg").write_bytes((c / "cover.jpg").read_bytes()); break

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2: sys.exit(__doc__)
    grab(args[0], pathlib.Path(args[1]), args[2] if len(args) > 2 else None)

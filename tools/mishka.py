#!/usr/bin/env python3
"""mishka.py <url> <dir> ["Title"] [--min-images N] [--max-chars N] [--split] [--dry]

Grabs illustrated tales from mishka-knizhka.ru into Lantern `story` packages. The page decides:
  * a LISTING (author / category page, paginated with page/N/) -> <dir> is a collection; every tale
    on it with at least N illustrations (default 4) is grabbed into <dir>/<slug>/
  * a TALE page -> <dir> is one story leaf: text.json (paragraphs), img/NN.jpg (the site's own
    illustrations, in reading order), scenes.json, cover.jpg (first illustration, square-cropped)
--max-chars N skips longer texts (author listings that mix in grown-up works); --split puts each tale of a
listing under <dir>/<its subsection>/ (the folk-tale listing: про животных / волшебные / бытовые).
--dry prints what a listing holds (title, image count, characters) and writes nothing.
Existing story dirs are skipped, so reruns are incremental."""
import html, io, json, pathlib, re, statistics, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"}
BASE = "https://mishka-knizhka.ru"
TALE = re.compile(r'href="(https://mishka-knizhka\.ru/(?:skazki-dlay-detey|rasskazy-dlya-detej|stihi-dlya-detej|basni)/(?:[^"/]+/){2,3})"')

def opt(name, default):
    return type(default)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default

MIN_IMAGES = opt("--min-images", 4)
MAX_CHARS = opt("--max-chars", 10**9)
SPLIT = "--split" in sys.argv  # listing tales go to <dir>/<their subsection>/<slug>/
DRY = "--dry" in sys.argv

def get(url, tries=3):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        except Exception as e:
            if i == tries - 1: raise
            print("  retry", url, e); time.sleep(3)

def text_of(frag):
    frag = re.sub(r"<br\s*/?>", "\n", frag)
    t = html.unescape(re.sub(r"<[^>]+>", "", frag)).replace("\xa0", " ")
    return "\n".join(re.sub(r"[ \t]+", " ", l).strip() for l in t.split("\n")).strip()

def clean_title(t):
    """'Колобок – русская народная сказка' → 'Колобок'; 'Птичка – Лев Толстой' → 'Птичка'."""
    head, sep, tail = t.rpartition(" – ")
    return head.strip() if sep and head and len(tail.split()) <= 5 else t.strip()

def is_verse(lines):
    return len(lines) >= 3 and statistics.median(len(l) for l in lines) < 55

def parse_tale(url):
    s = get(url).decode("utf-8", "replace")
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
    title = text_of(h1.group(1)) if h1 else url
    title = clean_title(title)
    a = s.find('<div class="read-content')
    b = s.find('class="add-fave-wrap"', a)
    body = s[a:b] if a > 0 else ""
    poem = re.search(r'class="entry-content[^"]*\bpoem\b', s) is not None
    paras, imgs, credit, stanza = [], [], [], []

    def flush():
        if stanza: paras.append("\n".join(stanza)); stanza.clear()

    for m in re.finditer(r"<(p|h[2-5]|figure|blockquote)\b[^>]*>(.*?)</\1>", body, re.S):
        inner = m.group(2)
        for im in re.findall(r'<img[^>]+src="([^"]+)"', inner):
            if "/wp-content/uploads/20" in im and im not in imgs:
                imgs.append(im); flush()
        if m.group(1) == "figure": continue
        t = text_of(inner)
        if not t: continue
        if re.match(r"(Иллюстрат|Художник|Рисунки|Иллюстрации)", t, re.I):
            credit.append(t); continue
        lines = [l for l in t.split("\n") if l]
        if poem and len(lines) == 1:
            # poems come one line per <p>: regroup into stanzas of ~8–16 lines at sentence ends
            stanza.append(lines[0])
            if (len(stanza) >= 8 and re.search(r"[.!?…»]\W*$", lines[0])) or len(stanza) >= 16: flush()
            continue
        flush()
        if len(lines) > 1 and not is_verse(lines):
            paras.extend(lines)  # prose broken with <br>: one paragraph per line
        else:
            paras.append("\n".join(lines))
    flush()
    return title, paras, imgs, credit

def square(im, size):
    w, h = im.size; s = min(w, h)
    return im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)).resize((size, size), Image.LANCZOS)

def story(url, d, title=None):
    if (d / "node.yaml").exists():
        print("  skip (exists)", d.name); return True
    ptitle, paras, imgs, credit = parse_tale(url)
    title = title or ptitle
    chars = sum(map(len, paras))
    if len(imgs) < MIN_IMAGES or len(paras) < 2 or chars > MAX_CHARS:
        print(f"  skip {title}: {len(imgs)} pictures, {len(paras)} paragraphs, {chars} chars"); return False
    imgs = imgs[:len(paras)]  # placement needs a paragraph per picture
    (d / "img").mkdir(parents=True, exist_ok=True)
    def fetch(src):
        try: return Image.open(io.BytesIO(get(src))).convert("RGB")
        except Exception as e: print("  picture failed:", src, e)
    with ThreadPoolExecutor(4) as pool: pictures = list(pool.map(fetch, imgs))
    scenes = []
    for i, im in enumerate(pictures, 1):
        if im is None: continue
        if im.width > 1200: im = im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS)
        name = f"{i:02d}"
        im.save(d / "img" / f"{name}.jpg", quality=86, optimize=True)
        if not scenes: square(im, 768).save(d / "cover.jpg", quality=88, optimize=True)
        scenes.append({"img": name, "caption": ""})
    if credit: paras.append(credit[0])
    (d / "text.json").write_text(json.dumps(paras, ensure_ascii=False, indent=0))
    (d / "scenes.json").write_text(json.dumps(scenes, ensure_ascii=False, indent=0))
    (d / "node.yaml").write_text(f"type: story\ntitle: {json.dumps(title, ensure_ascii=False)}\n"
                                 f"text: text.json\nscenes: scenes.json\nimages: img\nsource: {url}\n")
    print(f"  ok {d.name}: {title} — {len(scenes)} pictures, {sum(map(len, paras))} chars"); time.sleep(1)
    return True

def listing(url):
    """Tale URLs on a listing page and all its page/N/ continuations, in site order."""
    seen, out, pages, todo = set(), [], set(), [url]
    sect = url.rstrip("/").rsplit("/", 1)[-1]
    while todo:
        u = todo.pop(0)
        if u in pages: continue
        pages.add(u)
        s = get(u).decode("utf-8", "replace")
        main = s[s.find("<main"):] if "<main" in s else s
        for m in TALE.finditer(main):
            t = m.group(1)
            # only this section's tales: the header and sidebars link to promoted tales elsewhere
            if t not in seen and "/page/" not in t and f"/{sect}/" in t: seen.add(t); out.append(t)
        for m in re.finditer(r'href="(' + re.escape(url.rstrip("/")) + r'/page/\d+/)"', s):
            if m.group(1) not in pages: todo.append(m.group(1))
    return out

def slug_of(u): return u.rstrip("/").rsplit("/", 1)[-1]

def grab(url, d, title=None):
    if TALE.fullmatch(f'href="{url}"') and "read-content" in get(url).decode("utf-8", "replace"):
        return story(url, d, title)
    tales = listing(url)
    print(f"listing {url}: {len(tales)} tales -> {d}")
    if DRY:
        for t in tales:
            tt, p, im, _ = parse_tale(t)
            print(f"  {len(im):3d} pic {sum(map(len, p)):6d} ch  {tt}  {t}")
        return
    d.mkdir(parents=True, exist_ok=True)
    if title and not (d / "node.yaml").exists():
        (d / "node.yaml").write_text(f"type: collection\ntitle: {json.dumps(title, ensure_ascii=False)}\nsource: {url}\n")
    for t in tales:
        try: story(t, (d / t.rstrip("/").split("/")[-2] if SPLIT else d) / slug_of(t))
        except Exception as e: print("  FAILED", t, e)
    for c in [d] + ([x for x in d.iterdir() if x.is_dir()] if SPLIT else []):
        cover_from_child(c)

def cover_from_child(d):
    if not (d / "cover.jpg").exists():
        for c in sorted(d.iterdir()):
            if (c / "cover.jpg").exists(): (d / "cover.jpg").write_bytes((c / "cover.jpg").read_bytes()); break

if __name__ == "__main__":
    args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] not in ("--min-images", "--max-chars")]
    if len(args) < 2: sys.exit(__doc__)
    grab(args[0], pathlib.Path(args[1]), args[2] if len(args) > 2 else None)

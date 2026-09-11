#!/usr/bin/env python3
"""nukadeti.py <listing-url> <collection-dir> ["Collection title"]

Turns a nukadeti.ru audio listing (e.g. https://nukadeti.ru/audioskazki/rasskazy-nosova) into a
Lantern collection of audio packages: <dir>/node.yaml + cover.jpg, and per tale
<dir>/<slug>/{<slug>.mp3, cover.jpg, node.yaml}. Existing mp3s are skipped (rerun = incremental).
The site serves the file via download/audio/<id>?h=<hash>&type=<t>, taken from the player's
data-files JSON on each tale page; the cover is the tale's first illustration, square-cropped."""
import html, json, pathlib, re, sys, time, urllib.parse, urllib.request
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"}
BASE = "https://nukadeti.ru"

def get(url, referer=None):
    h = dict(UA)
    if referer: h["Referer"] = referer
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=120).read()

def tales(listing_html):
    """hrefs that appear both as an image link (empty text) and as a title link."""
    seen, out = {}, []
    for m in re.finditer(r'<a[^>]+href="(/audioskazki/[^"]+)"[^>]*>(.*?)</a>', listing_html, re.S):
        href, text = m.group(1), html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        seen.setdefault(href, set()).add(bool(text))
        if text and href not in [o[0] for o in out]:
            out.append((href, text))
    return [(h, t) for h, t in out if seen[h] == {True, False}]

def slug_of(href):
    s = href.rsplit("/", 1)[-1].replace("_", "-")
    for p in ("nikolaj-nosov-", "nosov-"):
        if s.startswith(p): s = s[len(p):]
    return s

def square(src_bytes, dst, size=768):
    im = Image.open(__import__("io").BytesIO(src_bytes)).convert("RGB")
    w, h = im.size; s = min(w, h)
    im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)).resize((size, size), Image.LANCZOS)
    im.save(dst, quality=88, optimize=True)

def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    listing, out = sys.argv[1], pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    page = get(listing).decode("utf-8", "replace")
    title = sys.argv[3] if len(sys.argv) > 3 else html.unescape(re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S).group(1)).strip()
    if not (out / "node.yaml").exists():
        (out / "node.yaml").write_text(f"type: collection\ntitle: {json.dumps(title, ensure_ascii=False)}\nsource: {listing}\n")
    items = tales(page); print(f"{len(items)} tales in {listing}")
    for href, text in items:
        slug = slug_of(href); d = out / slug; d.mkdir(exist_ok=True)
        mp3, cover = d / f"{slug}.mp3", d / "cover.jpg"
        if mp3.exists() and cover.exists(): print("skip", slug); continue
        url = BASE + href; tp = get(url).decode("utf-8", "replace")
        m = re.search(r"data-files='(\[.*?\])'", tp)
        if not m: print("NO PLAYER", slug); continue
        f = json.loads(html.unescape(m.group(1)))[0]
        if not mp3.exists():
            data = get(f"{BASE}/download/audio/{f['i']}?h={f['h']}&type={f['t']}", referer=url)
            if data[:3] != b"ID3" and data[:2] not in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"): print("NOT MP3", slug, data[:40]); continue
            mp3.write_bytes(data)
            (d / "node.yaml").write_text(f"type: audio\ntitle: {json.dumps(f.get('title') or text, ensure_ascii=False)}\nfile: {mp3.name}\nsource: {url}\n")
            print(f"ok {slug}: {f.get('title')} {f.get('duration')} {len(data)//1024} KB")
        if not cover.exists():
            # illustration from the tale's gallery, else the tale's own 400x400 tile, else og:image
            img = (re.search(r'href="(/content/images/essence/tale/\d+/\d+\.jpg)"', tp)
                   or re.search(rf'"(/content/images/static/tale400x400/{f.get("ei")}_\d+\.jpg)"', tp)
                   or re.search(r'"(/content/images/static/tale400x400/\d+_\d+\.jpg)"', tp)
                   or re.search(r'og:image" content="([^"]+)"', tp))
            if img:
                try: square(get(urllib.parse.urljoin(BASE, img.group(1))), cover); print("cover", slug, img.group(1))
                except Exception as e: print("cover failed", slug, e)
            else: print("NO COVER", slug)
        time.sleep(1)
    if not (out / "cover.jpg").exists():
        for d in sorted(out.iterdir()):
            if (d / "cover.jpg").exists(): (out / "cover.jpg").write_bytes((d / "cover.jpg").read_bytes()); break

if __name__ == "__main__":
    main()

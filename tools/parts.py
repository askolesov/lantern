#!/usr/bin/env python3
"""parts.py <manifest.json> <dir>

Builds a Lantern collection of numbered audio leaves from a manifest:
  {"title": "Снежная королева", "cover": "<image url>", "source": "<page url>",
   "parts": [{"title": "Зеркало и его осколки", "url": "<mp3 url>"}, …]}
-> <dir>/node.yaml + cover.jpg, and <dir>/NN-<slug>/{<slug>.mp3, cover.jpg, node.yaml} per part.
Existing files are skipped. Site adapters (knigavuhe.py, …) print such manifests."""
import io, json, pathlib, re, sys, time, urllib.request
from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"}

def get(url, referer=None, tries=3):
    h = dict(UA)
    if referer: h["Referer"] = referer
    for i in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=300).read()
        except Exception as e:  # IncompleteRead, timeouts: retry
            if i == tries - 1: raise
            print("  retry", i + 1, url[-40:], e); time.sleep(5)

def slugify(text, fallback="part"):
    tr = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", ["a","b","v","g","d","e","yo","zh","z","i","j","k","l","m","n","o","p","r","s","t","u","f","h","c","ch","sh","sch","","y","","e","yu","ya"]))
    s = re.sub(r"[^a-z0-9]+", "-", "".join(tr.get(c, c) for c in text.lower())).strip("-")
    return s[:40].rstrip("-") or fallback

def square(data, dst, size=768):
    im = Image.open(io.BytesIO(data)).convert("RGB"); w, h = im.size; s = min(w, h)
    im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)).resize((size, size), Image.LANCZOS).save(dst, quality=88, optimize=True)

def yaml_str(s): return json.dumps(s, ensure_ascii=False)

def main():
    if len(sys.argv) != 3: sys.exit(__doc__)
    m = json.load(open(sys.argv[1])); d = pathlib.Path(sys.argv[2]); d.mkdir(parents=True, exist_ok=True)
    if not (d / "node.yaml").exists():
        (d / "node.yaml").write_text(f"type: collection\ntitle: {yaml_str(m['title'])}\nsource: {m.get('source', '')}\n")
    cover = d / "cover.jpg"
    if not cover.exists() and m.get("cover"):
        try: square(get(m["cover"], m.get("source")), cover)
        except Exception as e: print("cover failed:", e)
    for i, p in enumerate(m["parts"], 1):
        title = p["title"] if not re.fullmatch(r"\d+", p["title"].strip()) else f"Часть {i}"
        slug = slugify(title, f"part-{i}"); pd = d / f"{i:02d}-{slug}"; pd.mkdir(exist_ok=True)
        mp3 = pd / f"{slug}.mp3"
        if not mp3.exists():
            data = get(p["url"], m.get("source"))
            if data[:3] != b"ID3" and data[:2] not in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"): print("NOT MP3:", title, data[:30]); continue
            mp3.write_bytes(data); print(f"ok {pd.name}: {title} {len(data)//1024} KB"); time.sleep(1)
        if not (pd / "node.yaml").exists():
            (pd / "node.yaml").write_text(f"type: audio\ntitle: {yaml_str(title)}\nfile: {mp3.name}\nsource: {p.get('source') or m.get('source', '')}\n")
        if not (pd / "cover.jpg").exists() and cover.exists(): (pd / "cover.jpg").write_bytes(cover.read_bytes())

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Download Comfortaa + Literata (cyrillic + latin) woff2 from Google Fonts into
internal/web/static/fonts/. Run once; the files are committed."""
import re, urllib.request, pathlib
OUT = pathlib.Path(__file__).resolve().parent.parent / "internal/web/static/fonts"
OUT.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
WANT = {
    ("Comfortaa", "normal", "cyrillic"): "comfortaa-cyrillic.woff2",
    ("Comfortaa", "normal", "latin"): "comfortaa-latin.woff2",
    ("Literata", "normal", "cyrillic"): "literata-cyrillic.woff2",
    ("Literata", "normal", "latin"): "literata-latin.woff2",
    ("Literata", "italic", "cyrillic"): "literata-italic-cyrillic.woff2",
    ("Literata", "italic", "latin"): "literata-italic-latin.woff2",
}
url = "https://fonts.googleapis.com/css2?family=Comfortaa:wght@400..700&family=Literata:ital,wght@0,400..600;1,400&display=swap"
css = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA})).read().decode()
for block in re.findall(r"/\* (\w+) \*/\s*@font-face \{(.*?)\}", css, re.S):
    subset, body = block
    fam = re.search(r"font-family: '([^']+)'", body).group(1)
    style = re.search(r"font-style: (\w+)", body).group(1)
    src = re.search(r"url\(([^)]+)\)", body).group(1)
    name = WANT.get((fam, style, subset))
    if not name: continue
    data = urllib.request.urlopen(urllib.request.Request(src, headers={"User-Agent": UA})).read()
    (OUT / name).write_bytes(data); print(name, len(data))

#!/usr/bin/env python3
"""cover.py <package-dir> "<scene prompt>"
Generates a square cover.png/cover.jpg for a package with gpt-image-1 in the house style
(BASE_MID from tools/book/gen_images.py). Costs real money (~$0.07): only run when asked.
Key: export $(grep -v '^#' ~/Documents/projects-my/life/dossiers/2026-08-local-ai-hardware/.env | xargs)
"""
import base64, json, os, pathlib, sys, urllib.request

BASE_MID = ("Classic children's book illustration in the manner of Inga Moore and Pauline Baynes: "
            "soft watercolor and fine ink line, warm natural colors, natural proportions, friendly "
            "open faces, gentle atmospheric light. A single clear subject filling the square frame, "
            "suitable as a cover thumbnail. No text, no letters, nothing frightening. ")

def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    d = pathlib.Path(sys.argv[1]); prompt = BASE_MID + sys.argv[2]
    key = os.environ.get("OPENAI_API_KEY") or sys.exit("OPENAI_API_KEY not set")
    body = json.dumps({"model": "gpt-image-1", "prompt": prompt, "size": "1024x1024", "quality": "medium", "n": 1}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=body,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        b64 = json.load(r)["data"][0]["b64_json"]
    png = d / "cover.png"; png.write_bytes(base64.b64decode(b64))
    from PIL import Image
    Image.open(png).convert("RGB").resize((768, 768), Image.LANCZOS).save(d / "cover.jpg", quality=88, optimize=True)
    png.unlink()
    print("wrote", d / "cover.jpg")

if __name__ == "__main__":
    main()

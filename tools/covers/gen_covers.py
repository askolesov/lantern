#!/usr/bin/env python3
"""Generate square section covers (the five root tiles) via OpenAI gpt-image-1.
Run from the content dir: `python3 ~/Documents/projects-my/lantern/tools/covers/gen_covers.py [dir …]`
(no args = every section whose cover is missing). Keys: source life/dossiers/2026-08-local-ai-hardware/.env
first. Cost: 1024x1024 medium ≈ $0.04 per picture. Existing covers are NOT overwritten — delete first.

Two prompt sets: SECTIONS is the live one (2026-09-12: one scene and one dominant color per section);
BEAR is an alternative "same bear cub on every tile" set, generated once and rejected — kept for reference."""
import base64, io, json, os, pathlib, sys, urllib.request
from PIL import Image

KEY = os.environ.get("OPENAI_API_KEY") or sys.exit("OPENAI_API_KEY not set")
BASE = ("Classic children's picture-book illustration for a 4-6 year old, warm watercolor and ink in the spirit of "
        "Inga Moore and Pauline Baynes: friendly, expressive, slightly stylized characters with natural proportions, "
        "warm rich colors, soft glowing light, no text, no letters, no logos. ")
SECTIONS = {
 "audio":           "Dominant color warm orange-yellow. A cozy old wooden radio with a round speaker grille and a glowing "
                    "dial stands on a rug; a fluffy red fox and a small grey hare sit in front of it listening with big "
                    "smiles, chins on paws; a teacup and a lamp beside them; daytime, sunny room.",
 "video":           "Dominant color sky blue. A friendly old television set with a rounded screen and two antenna ears "
                    "stands on a low table; on its screen a wolf and a hare from a cartoon chase each other; in front of "
                    "it, seen from behind, a little cat and a hedgehog sit on a cushion watching, popcorn bowl between them.",
 "books":           "Dominant color forest green. A big open storybook lying on a table, and out of its pages rises a "
                    "little painted world: a green hill with a round hobbit door, a tiny dragon curling like smoke, a far "
                    "lonely mountain; a reading lamp and glasses beside the book; warm evening light.",
 "lullabies-audio": "Dominant color deep violet-blue night. A sleeping teddy bear tucked under a striped blanket in a "
                    "small wooden bed, a crescent moon and a few soft stars through the window, a little music box on the "
                    "bedside table with gentle glowing musical notes floating up from it; a nightlight; peaceful.",
 "lullabies-video": "Dominant color dark teal night. A small cottage window seen from outside at night, warm light in "
                    "the glass, a sleepy cat curled on the window sill; above the roof a big smiling full moon with "
                    "closed eyes and a string of stars like a mobile; snow-free summer garden with a lantern; peaceful.",
}
BASE_SCENE = ("A single clear subject filling the square frame, readable as a small icon. Nothing frightening. ")
HERO = ("The one and only character is a small round brown bear cub with a red knitted scarf, friendly face, "
        "sitting on the floor, seen from the front, centered in the square frame, medium shot, on a plain warm "
        "cream paper background with a soft round vignette; exactly one prop beside the cub; ")
BEAR = {
 "audio":     "the prop is a cozy old wooden radio with a round speaker grille and a glowing amber dial; the cub "
                      "leans an ear toward it, eyes closed, smiling; accent color warm orange.",
 "video":     "the prop is a friendly old television set with a rounded screen and two antenna ears, showing a "
                      "wolf chasing a hare; the cub sits in front of it watching, holding a small bowl of popcorn; "
                      "accent color sky blue.",
 "books":     "the prop is a big open storybook on the cub's lap; out of the pages rises a tiny green hill with "
                      "a round hobbit door and a little dragon like smoke; the cub reads with wide eyes; accent color "
                      "forest green.",
 "lullabies-audio": "the cub is asleep, tucked under a striped blanket with a pillow, and the prop is a little wooden "
                      "music box beside it with soft glowing musical notes floating up; a crescent moon glows above; "
                      "accent color deep violet-blue night, the vignette darker.",
 "lullabies-video": "the cub is drowsy, yawning, hugging a pillow, and the prop is a small nightlight lamp shaped like "
                      "a smiling full moon on a stand, casting a warm glow; a few stars floating above; accent color "
                      "dark teal night, the vignette darker.",
}

def gen(name, scene):
    out = pathlib.Path(name) / "cover.jpg"
    if out.exists():
        return name, "skip (exists)"
    body = json.dumps({"model": "gpt-image-1", "prompt": BASE + BASE_SCENE + scene, "size": "1024x1024",
                       "quality": "medium", "n": 1}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=body,
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        b64 = json.load(r)["data"][0]["b64_json"]
    im = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB").resize((800, 800), Image.LANCZOS)
    im.save(out, quality=85, optimize=True)
    return name, "ok"

if __name__ == "__main__":
    only = sys.argv[1:]
    for name, scene in SECTIONS.items():
        if only and name not in only:
            continue
        if not pathlib.Path(name).is_dir():
            print(name, "no such dir"); continue
        print(*gen(name, scene), flush=True)

#!/usr/bin/env python3
"""Step 2 of the per-chapter workflow: picture placement over the CONDENSED text.

Run from the package dir (lantern-content/books/hobbit):
    python3 .../plan_slots.py 10              # slots for ch.10, spacing from the chapter length
    python3 .../plan_slots.py 10 --count 11   # force a slot count
    python3 .../plan_slots.py 10 --per 850    # force chars-per-picture (ch.3 spacing)
    python3 .../plan_slots.py 10 --skeleton   # + paste-ready SCENES / export.py stubs

For each slot it prints the WINDOW: the paragraphs from this anchor to the next one. Per the
project rule you then pick the most interesting moment INSIDE that window and write the prompt
for it -- the picture may sit a little above or below the exact sentence, but it must be the
best moment of that stretch, not simply the first paragraph.

Refuses to plan against text that is still full-length, because the anchors would be discarded
the moment the chapter is condensed.
"""
import argparse, json, pathlib, sys

TARGET_MAX = 12000  # condensed chapters run ~7.5-11.5k; anything above this is still full text

ap = argparse.ArgumentParser()
ap.add_argument("chapter", type=int)
ap.add_argument("--per", type=int, default=None, help="chars per picture (default: ~1000, the ch.5-9 spacing)")
ap.add_argument("--count", type=int, default=None, help="force number of slots")
ap.add_argument("--skeleton", action="store_true", help="print paste-ready SCENES / export.py stubs")
ap.add_argument("--force", action="store_true", help="plan anyway against full-length text")
ap.add_argument("--preview", type=int, default=160, help="chars of each paragraph to show")
a = ap.parse_args()

n = a.chapter
d = pathlib.Path(f"{n:02d}")
if (d / "text.json").exists():
    paras, src = json.load(open(d / "text.json")), f"{d}/text.json"
else:
    chs = json.load(open("src/condensed.json"))
    if not 1 <= n <= len(chs): sys.exit(f"chapter {n} not in src/condensed.json")
    ch = chs[n - 1]
    paras, src = (ch["paras"] if isinstance(ch, dict) else ch), "src/condensed.json"

paras = [p for p in paras if p.strip()]
total = sum(len(p) for p in paras)

if total > TARGET_MAX and not a.force:
    sys.exit(f"ch.{n} in {src} is {total} chars across {len(paras)} paras -- that is still FULL TEXT "
             f"(condensed chapters run ~7.5-11.5k).\nPlacement now would be thrown away when the chapter is "
             f"cut: every anchor moves. Condense first, then rerun.\nUse --force only to look at the shape.")

per   = a.per or 1000
count = a.count or max(1, round(total / per))
step  = total / count

print(f"ch.{n}  {src}  {total} chars, {len(paras)} paras -> {count} slots, ~{total // count} chars apart\n")

# anchor = first paragraph whose cumulative end passes each target offset
anchors, cum, tgt = [], 0, step / 2
for i, p in enumerate(paras):
    cum += len(p)
    while len(anchors) < count and cum >= tgt:
        anchors.append(i); tgt += step
while len(anchors) < count: anchors.append(len(paras) - 1)

for s, ai in enumerate(anchors):
    end = anchors[s + 1] if s + 1 < len(anchors) else len(paras)
    window = paras[ai:end] or [paras[ai]]
    wchars = sum(len(p) for p in window)
    print(f"--- slot {s+1}/{count}   anchor para {ai}   window paras {ai}..{max(ai,end-1)}   {wchars} chars")
    for j, p in enumerate(window):
        txt = p if len(p) <= a.preview else p[:a.preview].rstrip() + "..."
        print(f"    [{ai+j}] {txt}")
    print()

gaps = [anchors[i+1] - anchors[i] for i in range(len(anchors) - 1)]
if gaps: print(f"spacing check: min {min(gaps)} / max {max(gaps)} paragraphs between anchors")

if a.skeleton:
    print(f"\n# --- paste into gen_images.py SCENES (fill each prompt: exact characters present,\n"
          f"#     their state as the text has them -- on ponies if riding, chained if chained) ---")
    for s in range(count): print(f' "{n:02d}_SLUG{s+1}": "",')
    print(f"\n# --- paste into export.py scenes[{n-1}] (order + Russian captions) ---")
    print(f"{n-1}:[" + ",".join(f'("SLUG{s+1}","CAPTION{s+1}")' for s in range(count)) + "],")

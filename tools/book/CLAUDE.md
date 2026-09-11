# Hobbit pipeline (tools/book) — status 2026-09-11: ch. 1–7 COMPLETE (condensed + pictures); ch. 8 READY (prompts written, 12 pictures NOT generated ≈ $0.78); ch. 9–10 NOT READY (full text, old draft scenes)

**Where things are since 2026-09-11 (Lantern migration).** These scripts are the *tools*; the
*data* is the package `~/Documents/projects-my/lantern-content/books/hobbit/` (not in git):
`node.yaml`, `cover.jpg`, `book.json` (condensed text, written by `condense.py`), `scenes.json`
(scene order + captions, written by `export.py`), `img/chapter-N/*.{png,jpg}`; `src/` holds
`chapters.full.json`, `img-old/` (rejected pictures), the pre-migration `chapter-N.html` and
`build.py` as the rendering reference (delete once nobody needs them), `ch0N.txt`, `docs/`.
**All scripts run from the package dir:**
`cd ~/Documents/projects-my/lantern-content/books/hobbit && python3 ~/Documents/projects-my/lantern/tools/book/condense.py && python3 …/export.py`,
pictures: `python3 …/gen_images.py 08_* …` then `python3 …/shrink.py`. There is no `build.py`
any more: the Go server (`lantern serve`) renders `book.json` + `scenes.json` with the same
placement algorithm (golden-tested against the old HTML, `internal/book`). Scene order and
captions live in `export.py` (the old `scenes` dict), not in `build.py`.


Read `README.md` first (paths in it predate the move — see the box above) — it has the full pipeline, the image style prefix, character descriptions,
and the target picture density. Key rules:

- Never edit HTML: there is none. Scene order/captions → `export.py`, text → `condense.py`; rerun both from the package dir. The server picks up files on the next page load.
- **Ch. 1–3 are condensed for ~10 min read-aloud** (user request 2026-08-29), **ch. 4 onward for ~7 min (~7.5–8k chars; user decision 2026-09-04)**: their text lives in `condense.py` (CH1/CH2/CH4/CH5/CH6 = full rewritten lists, CH3 = REPL3/DROP3 overlay on `chapters.full.json`), which overwrites those chapters in `chapters.json`. Ch. 5 = 9.2k, ch. 6 = 9.5k chars (2026-09-05; ~8 min — a bit over target, riddles and the eagle scenes kept; cut further only if the user asks).
- **Names (user decision 2026-09-05): when condensing, rename Мешкинс → Бэггинс.** Implemented as `RENAME` in `condense.py`, applied to every chapter it writes (all 10, so the name is uniform across the reader); `chapters.full.json` keeps Мешкинс. New condensed text should be written with Бэггинс directly. Edit `condense.py`, then `python3 condense.py && python3 export.py` (from the package dir). Full original text is kept in `chapters.full.json`.
- **Per-chapter workflow (user decision 2026-09-02), strictly in this order:**
  1. Condense the chapter text (~7 min read-aloud, ~7.5–8k chars) in `condense.py`.
  2. Build, then determine the positions of the pictures spread evenly over the *condensed* text — **keep the ch. 3 spacing: one picture per ~850 chars, so ~10 per 8k-char chapter** (build.py places them by character count; print each picture's *window* = the paragraphs from its anchor to the next picture's anchor).
  3. Only then write the image prompts. For each window pick **the most interesting moment inside that window** (user decision 2026-09-04: the picture may sit a little above or below the exact sentence, but it must be the best moment of that stretch, not the first paragraph). The prompt must state **exactly the characters present and their state as the text has them**: if the company travels on ponies, EVERYONE is on ponies and the ponies appear in every travel/camp scene; if hands are chained, they are chained; name who is in the frame (Bilbo, Gandalf, Thorin, Fili & Kili, the Great Goblin…) — no generic "travelers", no hobbit on foot while the text says he rides. Ch. 1–3 pictures failed exactly on this (hobbit without a pony, odd elves, boring moments). Show the slot→prompt plan to the user before generating.
  Reason: chapters 1–2 pictures were generated from the full text before condensing and "absolutely didn't match context". Don't reuse old prompts for condensed chapters; if a chapter is condensed later, its pictures must be re-planned against the new text.
- **Never use global memory** (the `~/.claude/projects/.../memory/` directory). All project notes, decisions and lessons go in this file or `README.md`.
- Old pictures that no longer fit a re-planned chapter go to `src/img-old/chapter-N/` (not deleted). Ch. 5–6 old cute-style pictures (27 + 22) moved there 2026-09-05, ch. 7 old ones (11) 2026-09-07. Mixing kept old (cute-style) and new (realistic) pictures inside one chapter is accepted by the user to save credits (ch. 4: 4 old kept, 6 new — done 2026-09-04, the style break is visible; regenerate the 4 old ones if the user wants a uniform chapter).
- **Per-chapter status (update this table, not prose):**

  | Ch. | Text | Slots / prompts | Pictures |
  |---|---|---|---|
  | 1–4 | condensed | done | done |
  | 5 | condensed 9.2k | 11 (`05_*`) | done 2026-09-06 |
  | 6 | condensed 9.5k | 11 (`06_*`) | done 2026-09-08, `BASE_MID` style (1 regenerated: extra elf; reject in `_old/chapter-6/mid-rejects`) |
  | 7 | condensed 10.0k (2026-09-07) | 11 (`07_*`) | done 2026-09-10, `BASE_MID` style, all 11 accepted on contact sheet; old 11 in `_old` |
  | 8 | condensed 11.5k (2026-09-07, ~10 min — longest chapter, cut further only if asked) | 12 (`08_*`) | NOT generated (~$0.78) |
  | 9–10 | full text | old draft lists in `build.py` / `gen_images.py` (`9_*`, `10_*`) | 45 placeholders |

  Old `7_*`/`8_*` draft entries were removed from `gen_images.py` 2026-09-07 (still in `scenes_4_10.py`). **Always run `gen_images.py` with explicit scene names** — with no args it would also generate the 45 old ch. 9–10 drafts.
- New images: add to `SCENES` in `gen_images.py`, then `python3 gen_images.py [scene names…]` (no args = all missing), then `python3 shrink.py`.
  **Keys live in `~/Documents/projects-my/life/dossiers/2026-08-local-ai-hardware/.env`** (gitignored; user decision 2026-09-04): `OPENAI_API_KEY` (direct, gpt-image-1, ~$0.065/picture at medium 1536x1024 — preferred) and `OPENROUTER_API_KEY` (fallback backend in `gen_images.py`; use the `/images/generations` route, the chat route ignores size/quality and cost $0.28 for a square image). Load with `export $(grep -v '^#' <that .env> | xargs)`. Never copy a key into this folder.
- Keep `BASE` + per-scene `CHARS` injection in `gen_images.py` (never list all characters in the base prompt — it produces a 'cast lineup' in every image).
- **Style, three prefixes in `gen_images.py`, chosen per chapter via `BASE_BY_CH`:** `BASE_OLD` (ch. 1–3 and the kept old ch. 4 pictures: cute, toddler-ish — do not use), `BASE` (ch. 4–5: Alan Lee realism, user found it too dark/realistic), `BASE_MID` (ch. 6, user decision 2026-09-08: "a bit friendlier than the last time, not as friendly as the first wave" — Inga Moore / Pauline Baynes, warm colors, natural proportions, friendly faces). **`BASE_MID` is the confirmed house style for every new picture (user: "remember this style", 2026-09-08)** — it is `BASE_DEFAULT` in `gen_images.py`; `BASE` is pinned to ch. 4–5 only in `BASE_BY_CH`. Do not change the prefix without the user asking. Reference picture: `img/chapter-6/burglar_appears.jpg`.
- **Style for NEW pictures, original decision (2026-09-02):** less cutesy, more realistic — classic storybook drawings for a 4-year-old, not for a 1-year-old: natural proportions, real faces, real landscapes, atmospheric light, adventurous/mysterious mood allowed. Still nothing frightening or gory. The old "friendly rounded characters, everything gentle" prefix (used for ch. 1–6) is kept in `gen_images.py` as `BASE_OLD` for reference only; do not use it for new images.
- Density target: one picture per ~1400 characters of text; verify min/max spacing after build (snippet in README).
- Text source for further chapters: lyoshick.narod.ru/Texts/Tolk/HobbitNN.html.
- Image cost is real money (~$0.065 each at medium). Before any batch, tell the user the count and estimated cost and confirm; stop on repeated 429s — it means credits are out.
- **DO NOT generate images unless the user explicitly asks in the current session** (user decision 2026-08-28). Chapters 7–10 keep SVG placeholders for now.
- Product context / idea: docs/vision.md

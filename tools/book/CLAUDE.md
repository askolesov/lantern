# Hobbit pipeline (tools/book) — status 2026-09-16: ch. 1–19 COMPLETE, whole book condensed with real BASE_MID pictures, live on the node, unhidden, every chapter now on the current rules (ch. 1–5 were the last holdouts — BASE_OLD/BASE style, ch.1-3 on the old ~10 min target, ch.1-2 pictures made against the wrong text — all re-illustrated 2026-09-16, see the table below). Three reshoots total the same day from hallucinated/wrong content, all fixed by tightening the prompt: `15_gate_wall_built` (stray Gandalf+Bilbo in what should've been an empty shot), `19_auction_chaos` (literal "AUCTION" text on a sign), `02_troll_cave_treasure` (live trolls peering in when they were already stone statues outside by that point in the story) — see the CHARS/style notes below.

**Where things are since 2026-09-11 (Lantern migration).** These scripts are the *tools*; the
*data* is the package `~/Documents/projects-my/lantern-content/books/hobbit/` (not in git):
`node.yaml` (collection) + `cover.jpg`, then one **story** dir per chapter `NN/` with
`node.yaml` (title, label, `hidden: true` for a chapter until it has pictures — none hidden since 2026-09-16), `cover.jpg`
(= first scene), `text.json`, `scenes.json`, `img/<slug>.{png,jpg}`. `condense.py` writes
`src/condensed.json`; `export.py` splits it into the `NN/` dirs (never overwrites an existing
`node.yaml`). `src/` also holds `chapters.full.json`, `img-old/` (rejected pictures), the
pre-migration `chapter-N.html` + `build.py` as the rendering reference, `ch0N.txt`, `docs/`.
Image slugs stay `NN_slug` in `gen_images.py`; the file lands in `NN/img/slug.png`.
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
- **Names (user decision 2026-09-05): when condensing, rename Мешкинс → Бэггинс.** Implemented as `RENAME` in `condense.py`, applied to every chapter it writes (so the name is uniform across the reader); `chapters.full.json` keeps Мешкинс. New condensed text should be written with Бэггинс directly — this includes ch. 10 and every chapter of 11–19 as they get condensed, not just the original 10. Edit `condense.py`, then `python3 condense.py && python3 export.py` (from the package dir). Full original text is kept in `chapters.full.json`.
- **Per-chapter workflow (user decision 2026-09-02), strictly in this order:**
  1. Condense the chapter text (~7 min read-aloud, ~7.5–8k chars) in `condense.py`.
  2. Build, then determine the positions of the pictures spread evenly over the *condensed* text — **keep the ch. 3 spacing: one picture per ~850 chars, so ~10 per 8k-char chapter** (build.py places them by character count; print each picture's *window* = the paragraphs from its anchor to the next picture's anchor).
  3. Only then write the image prompts. For each window pick **the most interesting moment inside that window** (user decision 2026-09-04: the picture may sit a little above or below the exact sentence, but it must be the best moment of that stretch, not the first paragraph). The prompt must state **exactly the characters present and their state as the text has them**: if the company travels on ponies, EVERYONE is on ponies and the ponies appear in every travel/camp scene; if hands are chained, they are chained; name who is in the frame (Bilbo, Gandalf, Thorin, Fili & Kili, the Great Goblin…) — no generic "travelers", no hobbit on foot while the text says he rides. Ch. 1–3 pictures failed exactly on this (hobbit without a pony, odd elves, boring moments). Show the slot→prompt plan to the user before generating.
  Reason: chapters 1–2 pictures were generated from the full text before condensing and "absolutely didn't match context". Don't reuse old prompts for condensed chapters; if a chapter is condensed later, its pictures must be re-planned against the new text.
- **Never use global memory** (the `~/.claude/projects/.../memory/` directory). All project notes, decisions and lessons go in this file or `README.md`.
- Old pictures that no longer fit a re-planned chapter go to `src/img-old/chapter-N/` (not deleted). Ch. 5–6 old cute-style pictures (27 + 22) moved there 2026-09-05, ch. 7 old ones (11) 2026-09-07. Ch. 1–5 fully re-illustrated 2026-09-16 (see below) — no more mixed-style chapters left in the book.
- **Per-chapter status (update this table, not prose):**

  | Ch. | Text | Slots / prompts | Pictures |
  |---|---|---|---|
  | 1 | rewritten 2026-09-16, 17.1k→12.3k (~11 min — opening chapter, introduces the whole cast by name, same exception as ch.8/12) | 14 (`01_*`, `dwalin` added to `CHARS`) | done 2026-09-16, `BASE_MID`, all 14 accepted on contact sheet; old 23 BASE_OLD pictures archived to `src/img-old/chapter-1/` |
  | 2 | rewritten 2026-09-16, 12.8k→12.3k (~11 min, same exception) | 14 (`02_*`) | done 2026-09-16, `BASE_MID`, 13/14 accepted first pass; `troll_cave_treasure` reshot (see below); old 21 BASE_OLD pictures archived to `src/img-old/chapter-2/` |
  | 3 | unchanged 9.9k (~9 min, already at target) | 11 (`03_*`, re-planned — old plan had "hobbit without a pony, odd elves") | done 2026-09-16, `BASE_MID`, all 11 accepted on contact sheet; old 12 BASE_OLD pictures archived to `src/img-old/chapter-3/` |
  | 4 | unchanged, already correct | 10 (`04_*` — 4 of these, `crack_opens`/`goblin_hall`/`running_tunnels`/`dori_grabbed`, had never had proper prompts and were quietly missing until now, only old terse drafts in `scenes_4_10.py`) | done 2026-09-16, `BASE_MID` (was `BASE`, too dark/realistic); old 10 `BASE` pictures archived to `src/img-old/chapter-4-base/` |
  | 5 | unchanged, already correct | 11 (`05_*`) | done 2026-09-16, `BASE_MID` (was `BASE`); old 11 `BASE` pictures archived to `src/img-old/chapter-5-base/` |
  | 6 | condensed 9.5k | 11 (`06_*`) | done 2026-09-08, `BASE_MID` style (1 regenerated: extra elf; reject in `_old/chapter-6/mid-rejects`) |
  | 7 | condensed 10.0k (2026-09-07) | 11 (`07_*`) | done 2026-09-10, `BASE_MID` style, all 11 accepted on contact sheet; old 11 in `_old` |
  | 8 | condensed 11.5k (2026-09-07, ~10 min — longest chapter, cut further only if asked) | 12 (`08_*`) | done 2026-09-12, `BASE_MID`, all 12 accepted on contact sheet |
  | 9 | condensed 10.8k (2026-09-12, ~10 min — like ch. 7–8; cut further only if asked) | 11 (`09_*`) | done 2026-09-12, `BASE_MID`, all 11 accepted; `last_barrel` shows Bilbo visible among the elves (prompt asked for a faint outline) — regenerate if the user minds |
  | 10 | condensed 9.3k (2026-09-16, ~8 min) | 11 (`10_*`, re-planned against condensed text) | done 2026-09-16, `BASE_MID`, all 11 accepted on contact sheet; unhidden and synced |
  | 11 | condensed 7.9k (2026-09-16, ~7 min) | 9 (`11_*`) | done 2026-09-16, `BASE_MID`, all 9 accepted on contact sheet; unhidden and synced |
  | 12 | condensed 14.5k (2026-09-16, ~13 min — the Smaug chapter, kept longer than usual since it's the book's centerpiece; cut further only if asked) | 15 (`12_*`, `smaug`/`dragon` added to `CHARS` this chapter) | done 2026-09-16, `BASE_MID`, all 15 accepted on contact sheet; unhidden and synced |
  | 13 | condensed 8.9k (2026-09-16, ~8 min) | 9 (`13_*`) | done 2026-09-16, `BASE_MID`, all 9 accepted on contact sheet; unhidden and synced |
  | 14 | condensed 7.5k (2026-09-16, ~7 min) | 8 (`14_*`) | done 2026-09-16, `BASE_MID`, all 8 accepted on contact sheet; unhidden and synced |
  | 15 | condensed 10.2k (2026-09-16, ~9 min) | 11 (`15_*`) | done 2026-09-16, `BASE_MID`, 10/11 accepted first pass; `gate_wall_built` reshot (see below) |
  | 16 | condensed 7.2k (2026-09-16, ~7 min) | 8 (`16_*`) | done 2026-09-16, `BASE_MID`, all 8 accepted on contact sheet; unhidden and synced |
  | 17 | condensed 10.6k (2026-09-16, ~10 min — Battle of Five Armies, kept a bit longer) | 12 (`17_*`) | done 2026-09-16, `BASE_MID`, all 12 accepted on contact sheet; unhidden and synced |
  | 18 | condensed 9.7k (2026-09-16, ~9 min) | 10 (`18_*`) | done 2026-09-16, `BASE_MID`, all 10 accepted on contact sheet; unhidden and synced |
  | 19 | condensed 8.9k (2026-09-16, ~8 min) | 9 (`19_*`) | done 2026-09-16, `BASE_MID`, 8/9 accepted first pass; `auction_chaos` reshot (see below) |

  **Three reshoots so far, all fixed by tightening the prompt (lessons for future batches):**
  - `15_gate_wall_built` was meant to be an empty architectural landscape shot (no characters in the prompt at all), but the model hallucinated
    Gandalf and Bilbo standing in front of the wall anyway. Fix: explicitly add "No people or creatures anywhere in the scene, an empty
    architectural landscape shot." — a bare absence of character mentions isn't enough, say "empty" out loud.
  - `19_auction_chaos` asked for "a large auction notice pinned to the gate" and got a sign literally reading "AUCTION" in English letters,
    breaking the "no text, no letters" house rule. Fix: say "a blank unmarked notice board with no writing" instead of naming what the sign says.
  - `02_troll_cave_treasure` (ch. 1–5 batch) asked for "a troll cave" and got two live troll faces peering in from the side — but by that point
    in the story the trolls are already turned to stone outside in the daylight, so no troll should be present at all. Fix: say so explicitly,
    "no trolls or any other creature present (the trolls are already turned to stone outside)" — a location name alone ("troll cave") can pull
    in the owner as a hallucinated character even when the prompt never asks for them.
  Lesson from all three: when a scene includes a sign, a landscape, or a location tied to a character who *shouldn't* be in this particular
  moment, say so explicitly — don't rely on the base prompt's general "no text" / "only characters mentioned" clauses, or on the absence of a
  name, to hold on their own.

  Stub-placeholder mechanics (used for the first pass, kept here in case a future batch does the same): `export.py` only copies `cover.jpg` from
  the first scene if `cover.jpg` doesn't already exist, so once a stub cover exists it must be deleted (`rm NN/cover.jpg`) before re-running
  `export.py`, or the tile keeps showing the stub forever even after real art lands.

  Old `7_*`/`8_*` draft entries were removed from `gen_images.py` 2026-09-07, `9_*` on 2026-09-12 (all still in `scenes_4_10.py`). **Always run `gen_images.py` with explicit scene names** — with no args it would also generate the 14 old ch. 10 drafts.
  Lesson 2026-09-12, **fixed in code 2026-09-15**: the `CHARS` injection used to match substrings, so `himself`/`itself`/`shelf` injected the elf description
  and `Elvenking's caves` injects the king with his throne. `full_prompt()` now matches at a **word start** (`\b` + key), which kills the `himself`/`shelf`
  class of bug while keeping `dwar`→`dwarves`. Audit of all 132 `SCENES` entries found 3 prompts that the old matcher corrupted:
  `01_bilbo_burglar` and `10_master_feast` (`himself`) and **`06_eagle_lord_talks` (`shelf`) — a generated, live picture with a spurious elf in it;**
  regenerate it if the user minds. Semantic mismatches like `Elvenking's caves` are NOT fixed by the boundary — still say `the palace caves`,
  and preview with `python3 gen_images.py --dry-run <names…>`, which prints each prompt with the `CHARS` keys it injected and costs nothing.
  `gen_images.py` now **refuses to run with no scene names** (it would have generated the 14 stale `10_*` drafts); pass names, or `--all` to mean it.
  It also prints the picture count and estimated cost before generating.
- New images: add to `SCENES` in `gen_images.py`, then `python3 gen_images.py [scene names…]` (no args = all missing), then `python3 shrink.py`.
  **Keys live in `~/Documents/projects-my/life/dossiers/2026-08-local-ai-hardware/.env`** (gitignored; user decision 2026-09-04): `OPENAI_API_KEY` (direct, gpt-image-1, ~$0.065/picture at medium 1536x1024 — preferred) and `OPENROUTER_API_KEY` (fallback backend in `gen_images.py`; use the `/images/generations` route, the chat route ignores size/quality and cost $0.28 for a square image). Load with `export $(grep -v '^#' <that .env> | xargs)`. Never copy a key into this folder.
- Keep `BASE` + per-scene `CHARS` injection in `gen_images.py` (never list all characters in the base prompt — it produces a 'cast lineup' in every image).
- **Style, three prefixes in `gen_images.py`, chosen per chapter via `BASE_BY_CH`:** `BASE_OLD` (ch. 1–3 and the kept old ch. 4 pictures: cute, toddler-ish — do not use), `BASE` (ch. 4–5: Alan Lee realism, user found it too dark/realistic), `BASE_MID` (ch. 6, user decision 2026-09-08: "a bit friendlier than the last time, not as friendly as the first wave" — Inga Moore / Pauline Baynes, warm colors, natural proportions, friendly faces). **`BASE_MID` is the confirmed house style for every new picture (user: "remember this style", 2026-09-08)** — it is `BASE_DEFAULT` in `gen_images.py`; `BASE` is pinned to ch. 4–5 only in `BASE_BY_CH`. Do not change the prefix without the user asking. Reference picture: `img/chapter-6/burglar_appears.jpg`.
- **Style for NEW pictures, original decision (2026-09-02):** less cutesy, more realistic — classic storybook drawings for a 4-year-old, not for a 1-year-old: natural proportions, real faces, real landscapes, atmospheric light, adventurous/mysterious mood allowed. Still nothing frightening or gory. The old "friendly rounded characters, everything gentle" prefix (used for ch. 1–6) is kept in `gen_images.py` as `BASE_OLD` for reference only; do not use it for new images.
- Density target: one picture per ~1400 characters of text; verify min/max spacing after build (snippet in README).
- Text source for further chapters: lyoshick.narod.ru/Texts/Tolk/HobbitNN.html.
- Image cost is real money (~$0.065 each at medium). Before any batch, tell the user the count and estimated cost and confirm; stop on repeated 429s — it means credits are out.
- **DO NOT generate images unless the user explicitly asks in the current session** (user decision 2026-08-28). Chapter 10 keeps placeholders for now.
- Product context / idea: docs/vision.md

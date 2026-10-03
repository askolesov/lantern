# tools — everything that *produces* content packages

Hard boundary: nothing here is imported by the Go server, nothing here ships in the Docker
image (`.dockerignore`), and the only contract between this directory and the player is the
package format in `docs/specs/2026-09-11-lantern-design.md` §2. Python lives only here.

| Tool | What it does |
|---|---|
| `yt.sh <url> <dir>` | yt-dlp → `<dir>/video.mp4` (h264/aac ≤1080p, plays in Safari without transcoding), `cover.jpg` from the thumbnail, `node.yaml` draft with the video title. Fix the title by hand. |
| `audio.sh <file.mp3> <dir>` | copies the file into `<dir>` and writes a `node.yaml` draft. |
| `cover.py <dir> "<prompt>"` | square cover via gpt-image-1 in the house `BASE_MID` style. Key from `life/dossiers/2026-08-local-ai-hardware/.env`. ~$0.07 per cover — never run without being asked. |
| `nukadeti.py <url> <dir> ["Title"] [--numbered]` | nukadeti.ru → packages. A listing page becomes a collection of its tales (recursively, `--numbered` keeps the site's order); a multi-part page becomes a collection of `NN-<part>` leaves; a single tale becomes one leaf. mp3 via the site's download endpoint (player JSON), cover = tale illustration, square-cropped. Incremental. |
| `parts.py <manifest.json> <dir>` | generic: a manifest `{title, cover, source, parts:[{title,url}]}` → collection of `NN-<slug>` audio leaves. For any site once you have the mp3 URLs. |
| `knigavuhe.py <book-url> ["Title"]` | prints a `parts.py` manifest from a knigavuhe.org book page (its BookPlayer JSON: tracks, cover). Track titles there are numbers → «Часть N». |
| `mishka.py <url> <dir> ["Title"] [--min-images N] [--dry]` | mishka-knizhka.ru → illustrated `story` packages. A listing (author/category page, `page/N/` followed) becomes a collection of the tales from that section with ≥N illustrations (default 4); a tale page becomes one story leaf: `text.json`, `img/NN.jpg` (the site's own pictures in reading order), empty captions, cover = first picture square-cropped. `--dry` lists title / pictures / characters. Incremental. |
| `book/` | the Hobbit pipeline (condense → export → gen_images → shrink). Hobbit-specific until a second book exists. Read `book/CLAUDE.md`. |

Requirements: `brew install yt-dlp ffmpeg`, Python 3 with `Pillow`.

Workflow for a new item: run the tool into `~/Documents/projects-my/lantern-content/<collection>/<slug>/`,
edit `node.yaml`, then `make check sync` from this repo.

## Site notes (what we learned, 2026-09-11)

- **nukadeti.ru** — best first stop for Russian children's audio. Search: `/search?q=…`. Sections
  `/audioskazki/…` and `/audiorasskazy/…` (the Gav cycle lives in the second; `nukadeti.py` follows
  sub-tiles only under `/audioskazki/`, but any page URL can be given directly). A page's player
  carries `data-files` JSON: one entry per part with `i`, `h`, `t` → the file is
  `download/audio/<i>?h=<h>&type=<t>` (needs a Referer). Listing pages also carry the *first* tile's
  files — prefer the tiles. Long books are often split into named chapters (Urfin 33, Karlson 12,
  Prostokvashino per book); some are single files (Wizard 5h18, Snow Queen 1h12). Covers:
  illustration links `/content/images/essence/tale/<ei>/<n>.jpg`, else the tale's own
  `tale400x400/<ei>_<n>.jpg`. Image fetches sometimes time out — rerun, it fills covers only.
- **knigavuhe.org** — every book is a track list in `new BookPlayer(id, [...])`; direct mp3 URLs
  download with a Referer. Tracks are numbered, not named (`parts.py` → «Часть N»). Copyrighted
  authors (Nosov's Незнайка) show a placeholder book with 1 empty track or no player at all.
- **web-skazki.ru** — APlayer playlists (`{ name: 'Глава 1. …', url: '…/audio-files/….mp3' }`),
  chapters named, direct files, cover in `og:image`. Had Незнайка in 30 chapters.
- **аудиосказки-онлайн.рф** — named parts, but only `…/compress/` files at ~34 kbps; the
  uncompressed URLs 404. Used its part names, not its audio.
- **deti-online.com** — whole-book files in several versions, obfuscated `data-f` tokens (rot13
  path); not worth scripting.
- **YouTube** (`yt.sh`) — prefers h264/aac ≤1080p so Safari plays without transcoding; some videos
  only offer 360p in h264.
- **mishka-knizhka.ru** — the source for «Читать» (2026-10-02). Tale text sits in `div.read-content`
  (`page-wrap` divs, all pages in the HTML); pictures are `<figure>` or `<img>` inside a `<p>`, from
  `/wp-content/uploads/20…`. Poems (`entry-content … poem`) come one line per `<p>` — `mishka.py`
  regroups them into stanzas. Listing pages link promoted tales from other sections in the header,
  so only tales whose URL contains the listing's own segment are taken. Author listings live at short
  URLs (`/skazki-pushkina/`, `/rasskazy-nosova/`, `/stihi-chukovskogo/`, …); the folk-tale subsections at
  `/skazki-dlay-detey/russkie-narodnye-skazki/<sub>/`. A few long books are cut short for non-subscribers
  (Volkov's «Тайна заброшенного замка»: 805 characters) — check the `--dry` character count.
- **nukadeti.ru text tales** (`/skazki/…`) carry one picture per tale (the 400×400 tile) — useless for «Читать»;
  that is why the Read shelf comes from mishka-knizhka.ru.
- **The Read-shelf recipe (2026-10-02)**, rerunnable (incremental), from this dir, `B=../lantern-content/books`:
  `mishka.py <url> $B/<dir> "<Title>" [flags]` for each of —
  `/skazki-pushkina/` pushkin · `/russkie-narodnye-skazki/` russkie-narodnye `--split` (subsection collections'
  `node.yaml` written by hand: Про животных / Волшебные / Бытовые) · `/skazki-suteeva/` suteev ·
  `/stihi-chukovskogo/` + `/skazki-chukovskogo/` chukovsky · `/skazki-andersena/` andersen · `/skazki-bratev-grimm/` grimm ·
  `/skazki-sharlya-perro/` perrault · `/skazki-kiplinga/` kipling · `/rasskazy-nosova/` nosov · `/rasskazy-dragunskogo/`
  dragunsky · `/skazki-bianki/` bianki · `/skazki-marshaka/` marshak · `/skazki-uspenskogo/` uspensky · `/skazki-kozlova/`
  kozlov · `/skazki-zahodera/` zahoder · `/skazki-mihalkova/` mihalkov · `/skazki-shvarca/` shvarc · `/rasskazy-tolstogo-l-n/`
  lev-tolstoy `--max-chars 15000` · `/rasskazy-ushinskogo/` ushinsky · `/skazki-odoevskogo/` odoevsky · `/skazki-bazhova/` bazhov;
  single tale pages → `konek-gorbunok`, `alenkij-cvetochek`, `buratino`, `volkov/{volshebnik-izumrudnogo-goroda,urfin-dzhjus}`
  (`volkov/node.yaml` by hand). Then `group:` on each child of `books/` (see `CLAUDE.md`). 7 lists in parallel ≈ 1.5 h.
  Probed and absent (404): Мамин-Сибиряк, Пришвин, Гаршин, Токмакова, Даль, Родари, Линдгрен, Милн.

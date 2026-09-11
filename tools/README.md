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

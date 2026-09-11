# Lantern — design spec (2026-09-11)

A private, ad-free media shelf for a four-year-old: audio tales, cartoons and illustrated
books, on an iPad, with only parent-approved content. Grew out of the Hobbit illustrated
reader (2026-08/09), which becomes the first book package.

Personal project. Lives next to `life`, not in `sidequest-party` (no revenue goal). Code on
`github.com/askolesov/lantern`; content in a folder that is never in git.

## 1. Goals and non-goals

Goals
- The child navigates by pictures alone and picks what to listen to, watch or read.
- Adding content never touches code: drop a folder, sync, reload.
- One binary, one image, no database, no accounts, no state on the server.
- Works on iPad Safari at home (LAN) and away (Tailscale). Nothing public.

Non-goals (for now)
- Audio + timed picture slideshow (recognise speech → timestamps → generated pictures).
  Planned as a fourth node type later; the tree model must not block it.
- Learning content (letters, numbers). Same: a future node type.
- Parental controls, time limits, profiles, search. The whitelist is the filter; time is
  Guided Access / Screen Time on the tablet.
- Public hosting, Google indexing, copyright review. Content is private copies.

## 2. Content model — the tree

The content root is a directory. **A node is a directory that contains `node.yaml`.**
Directories without `node.yaml` are invisible to the scanner (used for `src/`, scratch).

Everything is explicit; one way to do one thing:
- type is declared in `node.yaml`, never inferred from the parent folder or extension;
- there are no implicit leaves (a bare `mp3` in a folder is ignored);
- children order = natural sort of directory names (`01`, `02`, … `10`); no `order` field.
  Want a different order → rename the directory;
- cover is `cover.jpg` | `cover.png` | `cover.webp` next to `node.yaml` (first found wins),
  required for every node including collections. Missing cover → `check` reports it and the
  UI shows a title tile instead. Never a hard error;
- a collection with a single child is not collapsed. A lone tale is a leaf without a wrapper.

### 2.1 `node.yaml`

Common header, all types:

```yaml
type: collection | audio | video | story
title: Простоквашино
hidden: false          # optional, default false — excluded from the UI, kept on disk
```

Type-specific tail:

```yaml
# audio / video
file: 01-dyadya-fyodor.mp3   # relative to this dir; mp3/m4a for audio, mp4/webm for video
source: https://…            # optional, provenance for the parent
```

```yaml
# story — ONE illustrated text (a short tale, or one chapter of a long book)
label: Глава 1       # optional small line above the title
text: text.json      # ["paragraph", …]
scenes: scenes.json  # [{img, caption}, …] in reading order
images: img          # dir holding <img>.jpg
```

`collection` has no tail; its children are the subdirectories that contain `node.yaml`.

**A book is not a type** (decision 2026-09-11): a long book is a `collection` of `story`
leaves, one per chapter, exactly as an audiobook is a collection of `audio` leaves. The
chapter list is the ordinary catalog grid; previous/next chapter is the ordinary sibling
navigation. A chapter that is not ready (text not condensed, no pictures) is `hidden: true`.

### 2.2 Example tree

```
content/
  audio/                 node.yaml (collection) + cover.jpg
    kolobok/             node.yaml (audio) + cover.jpg + kolobok.mp3
    prostokvashino/      node.yaml (collection) + cover.jpg
      01-dyadya-fyodor/  node.yaml (audio) + cover.jpg + 01.mp3
      02-mitroshkin/
  video/
    nu-pogodi/
      season-1/
        01/              node.yaml (video) + cover.jpg + 01.mp4
        02/
  books/
    hobbit/              node.yaml (collection) + cover.jpg
      01/                node.yaml (story) + cover.jpg + text.json + scenes.json + img/
      02/
      src/               NOT a node: full text, condensed.json, old pictures, old HTML
```

### 2.3 Validation

A broken node (yaml unparsable, unknown `type`, missing required field, referenced file
absent, path escaping the node dir) is logged and skipped by the server; the rest of the
tree still renders. `lantern check <dir>` runs the same scanner and prints every problem
with its path, exit code 1 if any. It is run on the Mac before syncing.

## 3. Screens

Target: iPad Safari, portrait and landscape; also a phone. The child is four but fluent
with devices: a children's UI, not a toddler's. Navigation is by covers; titles are small
and for the parent. Visual design is done separately in Claude Design from this spec; the
rules below are behaviour, not looks.

### 3.1 Catalog (`collection`, including root)

- Scrolling grid of cover tiles: 3–4 per row portrait, 5–6 landscape. Whole tile is the
  link. Title under the tile, small.
- Hidden nodes are omitted. A collection tile is visually distinguishable from a leaf
  (stack/folder cue), left to design.
- One large "back" control at top-left, absent on root. No breadcrumbs.

### 3.2 Audio player (`audio`)

- Cover large, title, then controls: previous, play/pause, next. Larger than adult
  controls, not toddler-sized. Thin seek bar, tap to seek.
- Previous/next = siblings in the same collection, in order. On `ended` → play next
  sibling automatically; on the last one, stop.
- Media Session API: cover, title, play/pause on the lock screen; audio continues with the
  screen off.
- Position saved to `localStorage` (key = node path) every few seconds; restored on open.
  No "start over" control: seek to 0.

### 3.3 Video player (`video`)

- Native `<video controls playsinline>` with `poster` = cover. Safari's own controls.
- Same sibling next/previous and autoplay-next as audio. No per-session cap.
- Position saved/restored like audio.

### 3.4 Story (`story`)

- One scrolling page: label + title, text with pictures placed by §5, bottom nav with
  previous / list / next (siblings in the collection; ends disabled).
- A book's chapter list is its collection page (§3.1); nothing book-specific exists.
- No reading-position memory (dropped 2026-09-11).

### 3.5 Full screen

Web app manifest + `apple-mobile-web-app-capable` so "Add to Home Screen" gives a
chrome-less app. Locking the child in is Guided Access, not the app.

## 4. Server

- `lantern serve --content DIR --addr :8080` and `lantern check DIR`. Go, standard library
  + `gopkg.in/yaml.v3`. Templates and static assets embedded (`embed`).
- **Scan per request.** Every page request walks the tree, parses yaml, sorts. Hundreds of
  nodes = milliseconds; no cache, no watcher, no restart to pick up new content. Add a cache
  only if it measurably lags.
- **Routes**
  - `GET /` → root catalog.
  - `GET /n/<path>` → node page by directory path from the content root (URL-encoded
    segments). Renders catalog / audio / video / story by `type`.
  - `GET /m/<path>/<file>` → media and covers from inside node `<path>`, served with
    `http.ServeFile` (Range requests, needed for Safari seeking). The resolved path must
    stay inside the node directory; otherwise 404.
  - `GET /static/…` → embedded CSS/JS, `GET /manifest.webmanifest`.
- Logging: one line per request (method, path, status, bytes, duration) to stdout.
  Nothing else.
- Errors: unknown path → 404 page in the same look; broken node → skipped (see §2.3).

## 5. Story rendering — port of `build.py`, one to one

Input: a story's `text.json` paragraphs and `scenes.json`.

1. **Paragraph splitting.** Paragraphs longer than 900 characters that contain no `\n`
   are split at sentence boundaries (`(?<=[.!?…»])\s+`), greedily packing sentences up to
   900 chars per piece. Paragraphs with `\n` (verse) are never split.
2. **Placement.** For a story with `S` scenes and paragraphs `p_0…p_n`, let `cum_i` be
   the character offset of `p_i` and `step = total_chars / (S − 0.5)`. For each scene
   `k = 0…S−1` in order, target `k·step`; place it before the not-yet-taken paragraph
   whose `cum_i` is closest to the target. First picture lands at the top, the last about
   half a step before the end.
3. **Figures.** Alternate `right` / `left` per figure, restarting with `right` on every
   story (build.py counted across the whole book; the per-story restart is the one
   deliberate deviation, 2026-09-11). Caption under the picture. Missing image →
   dimmed box, page still renders.
4. **Verse.** A paragraph with `\n` and under 600 chars gets `class="verse"`; `\n` → `<br>`.
5. **Page chrome.** Label line + title; bottom nav: previous, list, next (disabled at
   the ends). Reading column max 1000px, figures 58% wide floated with 32px gutter; under
   760px figures are full width, not floated. Fonts and colours per the Claude Design
   screens (`docs/design/`), the structure is fixed.

Verification of the port: a golden test reproduces build.py's (paragraph index → scene)
sequence for all ten Hobbit chapters (`internal/story/testdata`), and the migrated
package was rendered and compared figure-by-figure with the old HTML (2026-09-11: identical
for ch. 1–7, all images resolve).

## 6. Repository and content layout

```
~/Documents/projects-my/lantern/            git, github.com/askolesov/lantern
  cmd/lantern/                              main: serve, check
  internal/catalog/                         scanner, node types, validation, sorting
  internal/story/                           splitting + placement (§5), pure functions
  internal/web/                             handlers, templates, static, manifest
  tools/                                    everything that PRODUCES content; the server
                                            never imports it, only this dir may hold Python
    yt.sh <url> <dir>                       yt-dlp → video.mp4 (h264/aac ≤1080p, Safari-safe),
                                            cover.jpg from thumbnail, node.yaml draft
    audio.sh <file.mp3> <dir>               copies file, writes node.yaml draft
    cover.py <dir> "<prompt>"               gpt-image-1 square cover, BASE_MID style;
                                            key from life/dossiers/2026-08-local-ai-hardware/.env
    book/                                   the Hobbit pipeline, moved as is:
      condense.py gen_images.py shrink.py   (condensed text and scene prompts still inside
      export.py                             them — Hobbit-specific until a second book);
                                            export.py writes NN/{node.yaml,text.json,scenes.json,cover.jpg}
      README.md CLAUDE.md                   the old Hobbit rules, paths corrected
  deploy/                                   Dockerfile, k8s manifests (see §7)
  testdata/content/                         small fixture tree for tests
  docs/specs/, docs/plans/
  Makefile                                  build, test, image, sync

~/Documents/projects-my/lantern-content/    NOT git — source of truth AND the backup
  audio/  video/  books/hobbit/…            the tree of §2
```

**Player and tools do not mix** (decision 2026-09-11). Same repo, hard boundary:
- `tools/` is not part of the Go module and is excluded from the Docker image
  (`.dockerignore`), so the binary cannot depend on it;
- no code is shared in either direction — the only contract is the package format of §2;
- `tools/` has its own `README.md`; it is the one place where Python lives.

Hobbit migration splits the old folder in two:
- **Tools → `lantern/tools/book/`**: `condense.py`, `gen_images.py`, `shrink.py`,
  `scenes_*.py`, old `CLAUDE.md`/`README.md`. `build.py` is replaced by `export.py`, which
  splits `src/condensed.json` (written by `condense.py`) into per-chapter story dirs and
  carries the old `scenes` dict. Every script takes the package dir as an argument
  (`python3 tools/book/export.py ../lantern-content/books/hobbit`); nothing in `tools/`
  assumes a fixed content path.
- **Data → `lantern-content/books/hobbit/`**: `node.yaml` (collection) + `cover.jpg`, then
  `NN/` per chapter (`node.yaml` story, `cover.jpg`, `text.json`, `scenes.json`, `img/`);
  `src/` holds `chapters.full.json`, `condensed.json` (condense.py output), `img-old/`,
  and the old `chapter-N.html` + `build.py` kept as the rendering reference (port verified
  2026-09-11; delete when convenient). `src/` has no `node.yaml`, so the scanner ignores it.

The Python stays Hobbit-specific (condensed text and scene prompts live inside the
scripts) until a second book exists; then that data moves into the package and `tools/book`
becomes generic.

`life/map.md`: the Hobbit line becomes a Lantern line (repo, content dir, cluster URL).

## 7. Build, deploy, sync, access

- **Image.** Multi-stage Dockerfile, final `FROM scratch` with the static binary.
  GitHub Actions builds and pushes `ghcr.io/askolesov/lantern:<tag>` on a version tag.
- **Cluster.** Namespace `lantern` on the existing single-node k3s (`sidequest-k3s`).
  Deployment (1 replica, image tag pinned), Service, static `local-path` PV/PVC at
  `/srv/lantern/content` on the node, Traefik IngressRoute `lantern.192-168-56-83.nip.io`.
  Manifests in `deploy/k8s/`, applied with `kubectl apply -k deploy/k8s`. Not in
  `gitops/deploy` and not an ArgoCD app: personal project, kept out of the product plane.
- **Sync.** `make sync` = `rsync -av --delete lantern-content/ sidequest-k3s:/srv/lantern/content/`
  after `lantern check`. The Mac folder is the master copy; the node has no other backup.
- **Access away from home.** Tailscale on the iPad; the node is already on the tailnet
  (`sidequest-exit`). Same LAN hostname resolves via Tailscale routing. No Cloudflare
  Tunnel, no public hostname, no auth in the app.

## 8. Testing

- `internal/catalog`: scan `testdata/content` → expected tree; broken nodes (bad yaml,
  unknown type, missing file, missing cover, path escape) are reported and skipped; natural
  sort (`2` before `10`); `hidden` excluded from children but present in `check` output.
- `internal/story`: splitting and placement as pure functions with table tests; a golden
  test that reproduces `build.py`'s placement for all ten Hobbit chapters (fixture = the
  pre-migration `chapters.json`, expected = paragraph indices parsed from the old HTML).
- `internal/web`: `httptest` — root renders children; leaf pages by type; sibling
  prev/next links; story figures in golden order with sides restarting per story; media
  served with `206` on a Range request; `../` in a media path → 404; unknown node → 404;
  hidden node → 404.
- `lantern check` exit codes on a clean and a broken fixture.
- Manual on iPad after first deploy: seek in video, audio with screen locked, home-screen
  app opens full screen, Tailscale from mobile data.

## 9. Order of work (for the plan)

1. Repo skeleton, `catalog` scanner + `check`, tests.
2. `story` port + golden test against `build.py`.
3. `web`: catalog, audio, video, story pages styled after the Claude Design screens.
4. Hobbit migration: pipeline to `tools/book/`, data to the content dir, `export.py`;
   run the port verification.
5. Dockerfile, Actions, k8s manifests, first deploy, `make sync`.
6. `tools/yt.sh`, `audio.sh`, `cover.py`; first cartoon and first audio tale.
7. `life/map.md` line; GitHub repo pushed.

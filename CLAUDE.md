# Lantern — working rules

Read `README.md`, then the spec in `docs/specs/`. Decisions live in the spec; update it when
one changes. No hidden memory: notes go here or in the spec.

- **Player and tools never mix.** `tools/` is not in the Go module and not in the image. The
  only contract is the package format (spec §2). Python lives only in `tools/`.
- **Explicit everything, one way to do one thing.** No implicit leaves, no `order:` field
  (rename dirs), cover by filename convention, type declared in `node.yaml`.
- **A book is a collection of `story` leaves.** No book type, no chapter routes.
- **Content is not in git.** `~/Documents/projects-my/lantern-content/` is the master copy and
  the backup; `make sync` pushes it to the node. Never generate images without being asked
  (real money); see `tools/book/CLAUDE.md`.
- `gofmt` + `go vet` + `go test ./...` before every commit. Templates and static assets are
  embedded; edit them under `internal/web/` and rebuild.
- Commits: conventional prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`).

## Shelf layout (user decision 2026-09-11)

- `audio/`: **short stories grouped by author** (`nosov/`, `dragunsky/` — title = author's name);
  **chapter books and series at the top level** (`neznajka/`, `karlson/`, `prostokvashino/` with one
  sub-collection per book, `sobachka-sonya/` with its two books, …). A cycle of short stories about
  one character (`kotenok-po-imeni-gav/`) is top-level too.
- Chapter dirs are `NN-<slug>/`; the catalog draws the position badge on every tile whose dir name
  starts with a digit, so chapters sharing one cover stay distinguishable (added 2026-09-11).
- `books/hobbit/NN/` chapter 10 is `hidden: true` until it has pictures (08–09 unhidden 2026-09-12).
- **Five top-level sections (user decision 2026-09-12), one shelf row:** `audio/` «Сказки аудио»,
  `video/` «Сказки видео» (ex-«Мультфильмы»), `books/` «Книги», `lullabies-audio/` «Колыбельные аудио»
  (mp3 from mishka-knizhka.ru, 10 time-tested songs: Soviet classics + two folk), `lullabies-video/`
  «Колыбельные видео» (mp4 ≤720p from YouTube via `yt-dlp`, original performers, 8 videos). **YouTube mp4 must be H.264:** `-f "bv*[vcodec^=avc1][height<=720]+ba[ext=m4a]/b[ext=mp4][vcodec^=avc1]" --merge-output-format mp4` — a plain `[ext=mp4]` filter returns AV1, which Safari/iPad shows as a crossed-out play button (bitten 2026-09-12, 5 of 8 files re-fetched). Check with `ffprobe -show_entries stream=codec_name`. No wrapper
  collection for lullabies. Time-tested songs only, no modern AI-generated lullabies. Song dirs `NN-<slug>/`,
  covers = site og:image / YouTube thumbnail. Root order is the natural sort of dir names
  (audio, books, lullabies-audio, lullabies-video, video) — rename dirs if a different order is wanted.
- **Section covers** are generated (gpt-image-1, 1024² medium ≈ $0.04, saved 800² jpg) by
  `tools/covers/gen_covers.py`, one dominant color + one object per section so the tiles are
  distinguishable at a glance; same house style as the Hobbit pictures. Never overwrites — delete first.
  Generated 2026-09-12 (five tiles). Real money: only on request.

## Operations

- **Cluster**: ns `lantern` on the sidequest k3s, `KUBECONFIG=~/.kube/sidequest.yaml` (the Makefile
  exports it). Image `ghcr.io/askolesov/lantern` is private → pulled with the `ghcr` secret copied
  from ns `hestia`. New release = bump `newTag` in `deploy/k8s/kustomization.yaml`, tag `vX.Y.Z`,
  push, wait for the `image` workflow, `make deploy`.
- **Content**: `make sync` (rsync over SSH, key `~/.ssh/id_ed25519`, registered on the node
  2026-09-11; rsync installed on the node the same day). `check` runs first and blocks on problems
  outside hidden subtrees. Never `tar` from macOS without `COPYFILE_DISABLE=1` (it leaves `._*`
  files on the volume).
- Do not create pods that mount the content PVC as root except as a deliberate one-off; the app
  mounts it read-only as uid 65534.

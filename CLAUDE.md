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

# Lantern (Фонарик)

A private, ad-free media shelf for a four-year-old: audio tales, cartoons and illustrated
stories on an iPad, with only parent-approved content. One Go binary serves a folder of
content packages; adding content never touches code.

- Spec: [`docs/specs/2026-09-11-lantern-design.md`](docs/specs/2026-09-11-lantern-design.md)
- Screens: [`docs/design/`](docs/design/) (Claude Design export)
- Content tools: [`tools/`](tools/README.md) — never imported by the server

## Content = a tree of packages

A node is a directory with `node.yaml`. Types: `collection`, `audio`, `video`, `story`.
Cover is `cover.jpg|png|webp` next to it. Children are ordered by natural sort of dir names.

```
content/
  node.yaml                     type: collection, title: Фонарик
  audio/kolobok/                node.yaml (audio, file: kolobok.mp3) + cover.jpg + kolobok.mp3
  video/nu-pogodi/01/           node.yaml (video, file: 01.mp4) + cover.jpg + 01.mp4
  books/hobbit/01/              node.yaml (story, text/scenes/images) + cover.jpg + text.json + scenes.json + img/
```

## Run

```
make run                # serves ~/Documents/projects-my/lantern-content on http://127.0.0.1:8080
make check              # validates the content dir (same scanner as the server)
make test
```

## Deploy

Image from GitHub Actions on a `v*` tag → `ghcr.io/askolesov/lantern` (private; the cluster pulls with the `ghcr` secret copied from ns `hestia`). Manifests in
`deploy/k8s/` (`make deploy`), content pushed with `make sync` (rsync to the node; the Mac
folder is the master copy). LAN + Tailscale only.

### First deploy (once)

```
ssh sidequest-k3s 'sudo apt install -y rsync && sudo mkdir -p /srv/lantern/content && sudo chown $USER /srv/lantern/content'
make sync                      # content → node over SSH (key: ~/.ssh/id_ed25519, registered on the node 2026-09-11)
make deploy                    # kubectl apply -k deploy/k8s (KUBECONFIG=~/.kube/sidequest.yaml)
open http://lantern.192-168-56-83.nip.io
```

Done 2026-09-11 except `apt install rsync` (needs sudo). The first content load went through a
temporary busybox pod mounting the PVC (`tar | kubectl exec -i … tar x`, then `chown -R 1000:1000`).

New release: bump `newTag` in `deploy/k8s/kustomization.yaml`, tag `vX.Y.Z`, push the tag,
wait for the `image` workflow, `make deploy`. New content: `make sync` only.

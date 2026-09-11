#!/usr/bin/env bash
# audio.sh <file.mp3|m4a> <package-dir> [title]
# Copies one audio file into a Lantern audio package and writes a node.yaml draft.
set -euo pipefail
src=${1:?usage: audio.sh <file> <dir> [title]}; dir=${2:?usage: audio.sh <file> <dir> [title]}
title=${3:-$(basename "${src%.*}")}
mkdir -p "$dir"
name=$(basename "$src")
cp "$src" "$dir/$name"
cat > "$dir/node.yaml" <<YAML
type: audio
title: "${title//\"/\\\"}"
file: $name
YAML
echo "wrote $dir/node.yaml — add cover.jpg (tools/cover.py) and check the title, then: make check sync"

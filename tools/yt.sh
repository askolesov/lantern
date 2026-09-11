#!/usr/bin/env bash
# yt.sh <youtube-url> <package-dir>
# Downloads one video as a Lantern video package: video.mp4 + cover.jpg + node.yaml (draft).
set -euo pipefail
url=${1:?usage: yt.sh <url> <dir>}; dir=${2:?usage: yt.sh <url> <dir>}
mkdir -p "$dir"
# Safari-safe: h264 video + aac audio in mp4, at most 1080p. Falls back to the best mp4.
yt-dlp --no-playlist \
  -f 'bv*[vcodec^=avc1][height<=1080]+ba[acodec^=mp4a]/b[ext=mp4][height<=1080]/b' \
  --merge-output-format mp4 --remux-video mp4 \
  --write-thumbnail --convert-thumbnails jpg \
  -o "$dir/video.%(ext)s" "$url"
title=$(yt-dlp --no-playlist --print '%(title)s' "$url")
mv "$dir/video.jpg" "$dir/cover.jpg"
cat > "$dir/node.yaml" <<YAML
type: video
title: "${title//\"/\\\"}"
file: video.mp4
source: $url
YAML
echo "wrote $dir: $(ls "$dir" | tr '\n' ' ')"
echo "now edit $dir/node.yaml (title), then: make check sync"

#!/usr/bin/env python3
"""knigavuhe.py <book-url> ["Title"]  -> prints a parts.py manifest (JSON) to stdout.
Reads the page's BookPlayer JSON: track urls, durations, cover. Track titles there are usually
just numbers, so parts.py names them «Часть N»."""
import json, re, sys, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"}
url = sys.argv[1]
s = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "replace")
i = s.index("new BookPlayer("); tracks, _ = json.JSONDecoder().raw_decode(s[s.index("[", i):])
title = sys.argv[2] if len(sys.argv) > 2 else tracks[0]["player_data"]["title"]
print(json.dumps({"title": title, "cover": tracks[0]["player_data"].get("cover"), "source": url,
                  "parts": [{"title": t["title"], "url": t["url"], "duration": t.get("duration")} for t in tracks]}, ensure_ascii=False, indent=1))

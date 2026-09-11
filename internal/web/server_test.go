package web

import (
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
)

func TestMain(m *testing.M) {
	log.SetOutput(io.Discard)
	os.Exit(m.Run())
}

func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	s, err := New("../../testdata/content")
	if err != nil {
		t.Fatal(err)
	}
	ts := httptest.NewServer(s)
	t.Cleanup(ts.Close)
	return ts
}

func get(t *testing.T, ts *httptest.Server, path string) (int, string) {
	t.Helper()
	r, err := http.Get(ts.URL + path)
	if err != nil {
		t.Fatal(err)
	}
	defer r.Body.Close()
	var b strings.Builder
	buf := make([]byte, 64<<10)
	for {
		n, err := r.Body.Read(buf)
		b.Write(buf[:n])
		if err != nil {
			break
		}
	}
	return r.StatusCode, b.String()
}

func TestRootCatalog(t *testing.T) {
	ts := newTestServer(t)
	code, body := get(t, ts, "/")
	if code != 200 {
		t.Fatalf("status %d", code)
	}
	for _, want := range []string{"Фонарик", `href="/n/audio"`, "Сказки", "Книги", `class="tile stack"`, "/static/app.css"} {
		if !strings.Contains(body, want) {
			t.Errorf("root missing %q", want)
		}
	}
	if strings.Contains(body, `class="back"`) {
		t.Error("root must not have a back button")
	}
	if !strings.Contains(body, `class="cover ph g`) || !strings.Contains(body, "<span>М</span>") {
		t.Error("video collection has no cover: placeholder tile with first letter expected")
	}
}

func TestCollectionHidesHiddenAndHasBack(t *testing.T) {
	ts := newTestServer(t)
	_, body := get(t, ts, "/n/audio")
	if strings.Contains(body, "Скрытая") {
		t.Error("hidden node listed")
	}
	if !strings.Contains(body, `class="back" href="/"`) {
		t.Error("back to root missing")
	}
	if !strings.Contains(body, `src="/m/audio/kolobok/cover.jpg"`) {
		t.Error("cover url")
	}
	code, _ := get(t, ts, "/n/audio/hidden-one")
	if code != 404 {
		t.Errorf("hidden node page: %d", code)
	}
	code, _ = get(t, ts, "/n/nope")
	if code != 404 {
		t.Errorf("unknown: %d", code)
	}
}

func TestAudioPlaylist(t *testing.T) {
	ts := newTestServer(t)
	_, body := get(t, ts, "/n/audio/prostokvashino/02-mitroshkin")
	m := regexp.MustCompile(`data-tracks='([^']+)' data-index="(\d+)"`).FindStringSubmatch(body)
	if m == nil {
		t.Fatal("no playlist")
	}
	var tracks []Track
	if err := json.Unmarshal([]byte(strings.ReplaceAll(m[1], "&#34;", `"`)), &tracks); err != nil {
		t.Fatal(err, m[1])
	}
	if len(tracks) != 3 || m[2] != "1" || tracks[2].File != "/m/audio/prostokvashino/10-zima/a.mp3" {
		t.Fatalf("tracks %+v index %s", tracks, m[2])
	}
	if !strings.Contains(body, `<audio id="media"`) || !strings.Contains(body, "Простоквашино") {
		t.Error("audio page content")
	}
}

func TestVideoPage(t *testing.T) {
	ts := newTestServer(t)
	_, body := get(t, ts, "/n/video/nu-pogodi/01")
	if !strings.Contains(body, `<video id="media" controls playsinline`) || !strings.Contains(body, `poster="/m/video/nu-pogodi/01/cover.jpg"`) {
		t.Error("video element")
	}
	if !strings.Contains(body, `id="prev" hidden`) || !strings.Contains(body, `id="next" hidden`) {
		t.Error("single episode: prev/next hidden")
	}
}

func TestMediaRangeAndTraversal(t *testing.T) {
	ts := newTestServer(t)
	f := filepath.Join("../../testdata/content/audio/kolobok/kolobok.mp3")
	if err := os.WriteFile(f, []byte("0123456789"), 0o644); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { os.WriteFile(f, nil, 0o644) })
	req, _ := http.NewRequest("GET", ts.URL+"/m/audio/kolobok/kolobok.mp3", nil)
	req.Header.Set("Range", "bytes=2-4")
	r, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer r.Body.Close()
	if r.StatusCode != 206 || r.Header.Get("Content-Range") != "bytes 2-4/10" {
		t.Errorf("range: %d %s", r.StatusCode, r.Header.Get("Content-Range"))
	}
	for _, bad := range []string{"/m/audio/kolobok/../../node.yaml", "/m/audio/kolobok/node.yaml", "/m/node.yaml", "/m/audio/kolobok/%2e%2e/%2e%2e/node.yaml"} {
		req, _ := http.NewRequest("GET", ts.URL+bad, nil)
		req.URL.Path = strings.TrimPrefix(bad, "") // keep raw
		r, err := http.DefaultClient.Do(req)
		if err != nil {
			t.Fatal(err)
		}
		r.Body.Close()
		if r.StatusCode == 200 {
			t.Errorf("%s served (%d)", bad, r.StatusCode)
		}
	}
}

func TestStoryPage(t *testing.T) {
	ts := newTestServer(t)
	_, body := get(t, ts, "/n/books/tiny")
	if !strings.Contains(body, `href="/n/books/tiny/01"`) || !strings.Contains(body, `src="/m/books/tiny/01/cover.jpg"`) || !strings.Contains(body, "Глава 1 · Начало") {
		t.Error("book collection lists chapters as tiles")
	}
	_, body = get(t, ts, "/n/books/tiny/01")
	// 3 paragraphs, 2 scenes -> figures before paragraph 0 and 2; first figure right, second left
	fig := regexp.MustCompile(`<figure class="(\w+)"><img src="([^"]+)"`).FindAllStringSubmatch(body, -1)
	if len(fig) != 2 || fig[0][1] != "right" || fig[1][1] != "left" || fig[0][2] != "/m/books/tiny/01/img/one.jpg" {
		t.Errorf("figures: %v", fig)
	}
	if !strings.Contains(body, `<p class="verse">Строка один<br>строка два</p>`) {
		t.Error("verse rendering")
	}
	if !strings.Contains(body, `<div class="num">Глава 1</div>`) || !strings.Contains(body, "<h2>Начало</h2>") {
		t.Error("heading")
	}
	if !strings.Contains(body, `href="/n/books/tiny/02"`) || !strings.Contains(body, `class="off"`) || !strings.Contains(body, `href="/n/books/tiny">`) {
		t.Error("prev/next/list nav")
	}
	_, body = get(t, ts, "/n/books/tiny/02")
	if !strings.Contains(body, `<figure class="right">`) {
		t.Error("figure sides restart per story")
	}
}

func TestStaticAndManifest(t *testing.T) {
	ts := newTestServer(t)
	for _, p := range []string{"/static/app.css", "/static/player.js", "/static/fonts/comfortaa-cyrillic.woff2", "/manifest.webmanifest", "/static/icon-180.png"} {
		if code, _ := get(t, ts, p); code != 200 {
			t.Errorf("%s: %d", p, code)
		}
	}
}

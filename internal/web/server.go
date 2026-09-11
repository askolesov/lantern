// Package web serves the Lantern pages. The content tree is rescanned on
// every page request; media is served with http.ServeFile (Range support).
package web

import (
	"embed"
	"encoding/json"
	"fmt"
	"hash/fnv"
	"html/template"
	"io/fs"
	"log"
	"net/http"
	"net/url"
	"path/filepath"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/askolesov/lantern/internal/book"
	"github.com/askolesov/lantern/internal/catalog"
)

//go:embed templates/*.html
var templateFS embed.FS

//go:embed static
var staticFS embed.FS

// Server holds the content root and parsed templates.
type Server struct {
	content string
	tmpl    *template.Template
	mux     *http.ServeMux
}

// New builds the handler for a content directory.
func New(content string) (*Server, error) {
	funcs := template.FuncMap{
		"nodeURL":  nodeURL,
		"mediaURL": mediaURL,
		"json":     toJSON,
		"lines":    func(s string) []string { return strings.Split(s, "\n") },
		"add":      func(a, b int) int { return a + b },
	}
	t, err := template.New("").Funcs(funcs).ParseFS(templateFS, "templates/*.html")
	if err != nil {
		return nil, err
	}
	s := &Server{content: content, tmpl: t, mux: http.NewServeMux()}
	static, _ := fs.Sub(staticFS, "static")
	s.mux.Handle("GET /static/", http.StripPrefix("/static/", http.FileServerFS(static)))
	s.mux.HandleFunc("GET /manifest.webmanifest", s.manifest)
	s.mux.HandleFunc("GET /m/{path...}", s.media)
	s.mux.HandleFunc("GET /n/{path...}", s.node)
	s.mux.HandleFunc("GET /{$}", s.node)
	return s, nil
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	lw := &logWriter{ResponseWriter: w, status: 200}
	s.mux.ServeHTTP(lw, r)
	log.Printf("%s %s %d %dB %s", r.Method, r.URL.Path, lw.status, lw.bytes, time.Since(start).Round(time.Millisecond))
}

type logWriter struct {
	http.ResponseWriter
	status int
	bytes  int
}

func (l *logWriter) WriteHeader(c int) { l.status = c; l.ResponseWriter.WriteHeader(c) }
func (l *logWriter) Write(b []byte) (int, error) {
	n, err := l.ResponseWriter.Write(b)
	l.bytes += n
	return n, err
}

func (s *Server) scan() (*catalog.Tree, error) {
	t, err := catalog.Scan(s.content)
	if err != nil {
		return nil, err
	}
	for _, p := range t.Problems {
		log.Printf("content: %s", p)
	}
	return t, nil
}

// ---- URL helpers ----

func nodeURL(p string) string {
	if p == "" {
		return "/"
	}
	return "/n/" + escapePath(p)
}

func mediaURL(n *catalog.Node, file string) string {
	return "/m/" + escapePath(n.Path) + "/" + escapePath(file)
}

func escapePath(p string) string {
	segs := strings.Split(p, "/")
	for i, s := range segs {
		segs[i] = url.PathEscape(s)
	}
	return strings.Join(segs, "/")
}

func toJSON(v any) template.JS {
	b, _ := json.Marshal(v)
	return template.JS(b)
}

// ---- view models ----

type Tile struct {
	URL      string
	Title    string
	Cover    string // media URL or ""
	Letter   string
	Gradient int
	Stack    bool
	Current  bool
}

type Track struct {
	Path  string `json:"path"`
	URL   string `json:"url"`
	Title string `json:"title"`
	File  string `json:"file"`
	Cover string `json:"cover"`
}

type page struct {
	Title    string
	Node     *catalog.Node
	Parent   *catalog.Node
	BackURL  string
	IsRoot   bool
	Tiles    []Tile
	Tracks   []Track
	Index    int
	Cover    string
	Letter   string
	Gradient int
	Prev     *catalog.Node
	Next     *catalog.Node
	// chapter page
	Chapter      int
	Chapters     int
	ChapterNum   string
	ChapterTitle string
	Blocks       []block
	ListURL      string
	PrevURL      string
	NextURL      string
}

type block struct {
	Figure  bool
	Side    string
	Img     string
	Caption string
	Text    string
	Verse   bool
}

func tile(n *catalog.Node) Tile {
	t := Tile{URL: nodeURL(n.Path), Title: n.Title, Stack: n.Type == catalog.Collection,
		Letter: firstLetter(n.Title), Gradient: gradientOf(n.Path)}
	if n.Cover != "" {
		t.Cover = mediaURL(n, n.Cover)
	}
	return t
}

func firstLetter(s string) string {
	r, _ := utf8.DecodeRuneInString(strings.TrimSpace(s))
	if r == utf8.RuneError {
		return "?"
	}
	return strings.ToUpper(string(r))
}

func gradientOf(p string) int {
	h := fnv.New32a()
	h.Write([]byte(p))
	return int(h.Sum32() % 5)
}

func coverOf(n *catalog.Node) string {
	if n.Cover == "" {
		return ""
	}
	return mediaURL(n, n.Cover)
}

// ---- handlers ----

func (s *Server) render(w http.ResponseWriter, name string, p *page) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := s.tmpl.ExecuteTemplate(w, name, p); err != nil {
		log.Printf("render %s: %v", name, err)
	}
}

func (s *Server) notFound(w http.ResponseWriter) {
	w.WriteHeader(http.StatusNotFound)
	s.render(w, "404.html", &page{Title: "Не нашлось"})
}

func (s *Server) node(w http.ResponseWriter, r *http.Request) {
	t, err := s.scan()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	p := strings.Trim(r.PathValue("path"), "/")
	// "<path>/ch/<k>" → chapter of the book at <path>
	chapter := 0
	if segs := strings.Split(p, "/"); len(segs) >= 3 && segs[len(segs)-2] == "ch" {
		if k, err := strconv.Atoi(segs[len(segs)-1]); err == nil && k >= 1 {
			if b := t.Find(strings.Join(segs[:len(segs)-2], "/")); b != nil && b.Type == catalog.Book {
				chapter, p = k, b.Path
			}
		}
	}
	n := t.Find(p)
	if n == nil || (n.Hidden && n.Parent != nil) {
		s.notFound(w)
		return
	}
	pg := &page{Title: n.Title, Node: n, Parent: n.Parent, IsRoot: n.Parent == nil,
		Cover: coverOf(n), Letter: firstLetter(n.Title), Gradient: gradientOf(n.Path)}
	if n.Parent != nil {
		pg.BackURL = nodeURL(n.Parent.Path)
	}
	switch n.Type {
	case catalog.Collection:
		for _, c := range n.Visible() {
			pg.Tiles = append(pg.Tiles, tile(c))
		}
		s.render(w, "catalog.html", pg)
	case catalog.Audio, catalog.Video:
		for i, sib := range n.Siblings() {
			if sib.Type != n.Type {
				continue
			}
			if sib == n {
				pg.Index = len(pg.Tracks)
			}
			pg.Tracks = append(pg.Tracks, Track{Path: sib.Path, URL: nodeURL(sib.Path), Title: sib.Title,
				File: mediaURL(sib, sib.File), Cover: coverOf(sib)})
			_ = i
		}
		pg.Prev, pg.Next = n.PrevNext()
		if n.Type == catalog.Audio {
			s.render(w, "audio.html", pg)
		} else {
			s.render(w, "video.html", pg)
		}
	case catalog.Book:
		b, err := book.Load(n.Dir, n.Text, n.Scenes)
		if err != nil {
			log.Printf("book %s: %v", n.Path, err)
			s.notFound(w)
			return
		}
		pg.Chapters = len(b.Chapters)
		pg.ListURL = nodeURL(n.Path)
		if chapter == 0 {
			for i, ch := range b.Chapters {
				tl := Tile{URL: fmt.Sprintf("%s/ch/%d", nodeURL(n.Path), i+1), Title: ch.Num + " · " + ch.Title,
					Letter: strconv.Itoa(i + 1), Gradient: i % 5}
				if len(b.Scenes[i]) > 0 {
					tl.Cover = mediaURL(n, fmt.Sprintf("%s/chapter-%d/%s.jpg", n.Images, i+1, b.Scenes[i][0].Img))
				}
				pg.Tiles = append(pg.Tiles, tl)
			}
			s.render(w, "book.html", pg)
			return
		}
		if chapter > len(b.Chapters) {
			s.notFound(w)
			return
		}
		s.renderChapter(w, pg, n, b, chapter)
	}
}

func (s *Server) renderChapter(w http.ResponseWriter, pg *page, n *catalog.Node, b *book.Book, k int) {
	ch := b.Chapters[k-1]
	scenes := b.Scenes[k-1]
	pg.Chapter = k
	pg.ChapterNum = ch.Num
	pg.ChapterTitle = ch.Title
	pg.Title = ch.Num + ". " + ch.Title + " — " + n.Title
	places := book.Place(ch.Paras, len(scenes))
	at := map[int]int{}
	for si, pi := range places {
		at[pi] = si
	}
	fig := b.FigureOffset(k - 1)
	for pi, p := range ch.Paras {
		if si, ok := at[pi]; ok {
			side := "right"
			if fig%2 == 1 {
				side = "left"
			}
			fig++
			sc := scenes[si]
			pg.Blocks = append(pg.Blocks, block{Figure: true, Side: side, Caption: sc.Caption,
				Img: mediaURL(n, fmt.Sprintf("%s/chapter-%d/%s.jpg", n.Images, k, sc.Img))})
		}
		pg.Blocks = append(pg.Blocks, block{Text: p, Verse: book.IsVerse(p)})
	}
	if k > 1 {
		pg.PrevURL = fmt.Sprintf("%s/ch/%d", nodeURL(n.Path), k-1)
	}
	if k < len(b.Chapters) {
		pg.NextURL = fmt.Sprintf("%s/ch/%d", nodeURL(n.Path), k+1)
	}
	s.render(w, "chapter.html", pg)
}

func (s *Server) media(w http.ResponseWriter, r *http.Request) {
	t, err := s.scan()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	n, file := t.Resolve(r.PathValue("path"))
	if n == nil {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Cache-Control", "public, max-age=86400")
	http.ServeFile(w, r, filepath.Join(n.Dir, filepath.FromSlash(file)))
}

func (s *Server) manifest(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/manifest+json")
	json.NewEncoder(w).Encode(map[string]any{
		"name": "Фонарик", "short_name": "Фонарик", "start_url": "/", "display": "standalone",
		"background_color": "#fdf3e3", "theme_color": "#2b2033", "lang": "ru",
		"icons": []map[string]string{{"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"}},
	})
}

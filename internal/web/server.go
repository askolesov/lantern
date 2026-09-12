// Package web serves the Lantern pages. The content tree is rescanned on
// every page request; media is served with http.ServeFile (Range support).
package web

import (
	"embed"
	"encoding/json"
	"hash/fnv"
	"html/template"
	"io/fs"
	"log"
	"net/http"
	"net/url"
	"path"
	"path/filepath"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/askolesov/lantern/internal/catalog"
	"github.com/askolesov/lantern/internal/story"
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
	Path     string // node path, for the position-badge rule
	URL      string
	Title    string
	Cover    string // media URL or ""
	Letter   string
	Gradient int
	Stack    bool
	Num      int // 1-based position, shown as a badge when the dir name starts with a digit
}

// Group is one run of tiles on a catalog page: the children that share a
// `group:` label, under that label as a header. Groups come in the order the
// label first appears in the listing; children without a label form one
// untitled group at the end.
type Group struct {
	Title string
	Tiles []Tile
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
	Groups   []Group // catalog page
	Tracks   []Track
	Index    int
	Cover    string
	Letter   string
	Gradient int
	Prev     *catalog.Node
	Next     *catalog.Node
	Blocks   []block // story page
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
	t := Tile{Path: n.Path, URL: nodeURL(n.Path), Title: n.Title, Stack: n.Type == catalog.Collection,
		Letter: firstLetter(n.Title), Gradient: gradientOf(n.Path)}
	if n.Label != "" {
		t.Title = n.Label + " · " + n.Title
	}
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
		pg.Groups = groups(n)
		s.render(w, "catalog.html", pg)
	case catalog.Audio, catalog.Video:
		for _, sib := range n.Siblings() {
			if sib.Type != n.Type {
				continue
			}
			if sib == n {
				pg.Index = len(pg.Tracks)
			}
			pg.Tracks = append(pg.Tracks, Track{Path: sib.Path, URL: nodeURL(sib.Path), Title: sib.Title,
				File: mediaURL(sib, sib.File), Cover: coverOf(sib)})
		}
		pg.Prev, pg.Next = n.PrevNext()
		if n.Type == catalog.Audio {
			s.render(w, "audio.html", pg)
		} else {
			s.render(w, "video.html", pg)
		}
	case catalog.Story:
		st, err := story.Load(n.Dir, n.Text, n.Scenes)
		if err != nil {
			log.Printf("story %s: %v", n.Path, err)
			s.notFound(w)
			return
		}
		pg.Prev, pg.Next = n.PrevNext()
		pg.Blocks = blocks(n, st)
		s.render(w, "story.html", pg)
	}
}

// groups lays out the visible children of a collection by their `group:`
// label (see Group). Position badges count within each group.
func groups(n *catalog.Node) []Group {
	var out []Group
	index := map[string]int{}
	var loose []*catalog.Node
	for _, c := range n.Visible() {
		if c.Group == "" {
			loose = append(loose, c)
			continue
		}
		i, ok := index[c.Group]
		if !ok {
			i = len(out)
			index[c.Group] = i
			out = append(out, Group{Title: c.Group})
		}
		out[i].Tiles = append(out[i].Tiles, tile(c))
	}
	if len(loose) > 0 {
		g := Group{}
		for _, c := range loose {
			g.Tiles = append(g.Tiles, tile(c))
		}
		out = append(out, g)
	}
	for gi := range out {
		for i := range out[gi].Tiles {
			if base := path.Base(out[gi].Tiles[i].Path); base != "" && base[0] >= '0' && base[0] <= '9' {
				out[gi].Tiles[i].Num = i + 1
			}
		}
	}
	return out
}

// blocks interleaves figures and paragraphs: each scene goes before the
// paragraph chosen by story.Place; sides alternate right/left.
func blocks(n *catalog.Node, st *story.Story) []block {
	at := map[int]int{}
	for si, pi := range story.Place(st.Paras, len(st.Scenes)) {
		at[pi] = si
	}
	var out []block
	fig := 0
	for pi, p := range st.Paras {
		if si, ok := at[pi]; ok {
			side := "right"
			if fig%2 == 1 {
				side = "left"
			}
			fig++
			sc := st.Scenes[si]
			out = append(out, block{Figure: true, Side: side, Caption: sc.Caption,
				Img: mediaURL(n, n.Images+"/"+sc.Img+".jpg")})
		}
		out = append(out, block{Text: p, Verse: story.IsVerse(p)})
	}
	return out
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

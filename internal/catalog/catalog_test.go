package catalog

import (
	"strings"
	"testing"
)

func scanFixture(t *testing.T) *Tree {
	t.Helper()
	tr, err := Scan("../../testdata/content")
	if err != nil {
		t.Fatal(err)
	}
	return tr
}

func titles(ns []*Node) string {
	var s []string
	for _, n := range ns {
		s = append(s, n.Title)
	}
	return strings.Join(s, ",")
}

func TestScanTree(t *testing.T) {
	tr := scanFixture(t)
	if tr.Root.Title != "Фонарик" || tr.Root.Type != Collection {
		t.Fatalf("root: %+v", tr.Root)
	}
	if got := titles(tr.Root.Children); got != "Сказки,Книги,Сломанные,Мультфильмы" {
		t.Fatalf("root children: %s", got)
	}
	k := tr.Find("audio/kolobok")
	if k == nil || k.Type != Audio || k.File != "kolobok.mp3" || k.Cover != "cover.jpg" || k.Source == "" {
		t.Fatalf("kolobok: %+v", k)
	}
	if k.Parent != tr.Find("audio") {
		t.Fatal("parent link")
	}
}

func TestNaturalOrderAndNonNodes(t *testing.T) {
	tr := scanFixture(t)
	p := tr.Find("audio/prostokvashino")
	if got := titles(p.Children); got != "01-dyadya-fyodor,02-mitroshkin,10-zima" {
		t.Fatalf("order: %s", got)
	}
	if p.Cover != "cover.png" {
		t.Fatalf("cover: %s", p.Cover)
	}
	if tr.Find("audio/prostokvashino/src") != nil {
		t.Fatal("src without node.yaml must not be a node")
	}
}

func TestHidden(t *testing.T) {
	tr := scanFixture(t)
	a := tr.Find("audio")
	if got := titles(a.Children); !strings.Contains(got, "Скрытая") {
		t.Fatalf("hidden must be in Children: %s", got)
	}
	if got := titles(a.Visible()); strings.Contains(got, "Скрытая") {
		t.Fatalf("hidden must not be in Visible: %s", got)
	}
	h := tr.Find("audio/hidden-one")
	if h == nil || !h.Hidden {
		t.Fatal("hidden node must still be findable")
	}
	found := false
	for _, p := range tr.Problems {
		if p.Path == "audio/hidden-one" && !p.Hidden {
			t.Errorf("problem inside a hidden node must be marked hidden: %v", p)
		}
		if p.Path == "audio/hidden-one" && p.Hidden && strings.Contains(p.Msg, "missing cover") {
			found = true
		}
	}
	if !found {
		t.Error("hidden node without a cover must still be reported (as hidden)")
	}
}

func TestSiblings(t *testing.T) {
	tr := scanFixture(t)
	mid := tr.Find("audio/prostokvashino/02-mitroshkin")
	prev, next := mid.PrevNext()
	if prev.Title != "01-dyadya-fyodor" || next.Title != "10-zima" {
		t.Fatalf("prev=%v next=%v", prev, next)
	}
	first := tr.Find("audio/prostokvashino/01-dyadya-fyodor")
	if p, _ := first.PrevNext(); p != nil {
		t.Fatal("first has no prev")
	}
	last := tr.Find("audio/prostokvashino/10-zima")
	if _, n := last.PrevNext(); n != nil {
		t.Fatal("last has no next")
	}
	if p, n := tr.Root.PrevNext(); p != nil || n != nil {
		t.Fatal("root has no siblings")
	}
}

func TestStoryFields(t *testing.T) {
	tr := scanFixture(t)
	b := tr.Find("books/tiny/01")
	if b == nil || b.Type != Story || b.Text != "text.json" || b.Scenes != "scenes.json" || b.Images != "img" || b.Label != "Глава 1" {
		t.Fatalf("story: %+v", b)
	}
	if tr.Find("books/tiny").Type != Collection {
		t.Fatal("a book is a plain collection")
	}
}

func TestProblems(t *testing.T) {
	tr := scanFixture(t)
	want := map[string]string{
		"broken/no-file":      "file not found",
		"broken/bad-yaml":     "bad yaml",
		"broken/unknown-type": "unknown type",
		"broken/escape":       "escapes",
		"video":               "missing cover",
	}
	for p, msg := range want {
		found := false
		for _, pr := range tr.Problems {
			if pr.Path == p && strings.Contains(pr.Msg, msg) {
				found = true
			}
		}
		if !found {
			t.Errorf("expected problem %q containing %q; got %v", p, msg, tr.Problems)
		}
	}
	for _, p := range []string{"broken/no-file", "broken/bad-yaml", "broken/unknown-type", "broken/escape"} {
		if tr.Find(p) != nil {
			t.Errorf("%s must be skipped", p)
		}
	}
	if tr.Find("video") == nil {
		t.Error("missing cover must not drop the node")
	}
	for _, pr := range tr.Problems {
		if pr.Path == "" {
			t.Errorf("root cover must not be a problem: %v", pr)
		}
	}
}

func TestResolve(t *testing.T) {
	tr := scanFixture(t)
	n, f := tr.Resolve("audio/kolobok/kolobok.mp3")
	if n == nil || n.Path != "audio/kolobok" || f != "kolobok.mp3" {
		t.Fatalf("resolve: %v %q", n, f)
	}
	n, f = tr.Resolve("books/tiny/01/img/one.jpg")
	if n == nil || n.Path != "books/tiny/01" || f != "img/one.jpg" {
		t.Fatalf("resolve book: %v %q", n, f)
	}
	for _, bad := range []string{"audio/kolobok/../../node.yaml", "audio/kolobok/node.yaml", "audio/kolobok", "nope/x.mp3", "node.yaml", "cover.jpg", "audio/kolobok/../kolobok/kolobok.mp3"} {
		if n, f := tr.Resolve(bad); n != nil {
			t.Errorf("%q must not resolve, got %v %q", bad, n.Path, f)
		}
	}
}

package book

import (
	"encoding/json"
	"os"
	"reflect"
	"testing"
)

func TestSplitLong(t *testing.T) {
	if got := SplitLong("short. text", 900); len(got) != 1 {
		t.Fatal("short paragraph must not split")
	}
	verse := "a. b\nc. d"
	if got := SplitLong(verse, 2); len(got) != 1 {
		t.Fatal("verse must not split")
	}
	long := "Один два три. Четыре пять! Шесть семь? Восемь… Девять» Десять."
	got := SplitLong(long, 20)
	want := []string{"Один два три.", "Четыре пять!", "Шесть семь? Восемь…", "Девять» Десять."}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("got %q want %q", got, want)
	}
}

func TestPlaceSimple(t *testing.T) {
	paras := []string{"aaaa", "bbbb", "cccc", "dddd"} // cums 0,4,8,12; total 16
	// n=2: step = 16/1.5 = 10.67; k0 -> 0; k1 target 10.67 -> closest is 12 (idx 3)
	if got := Place(paras, 2); !reflect.DeepEqual(got, []int{0, 3}) {
		t.Fatalf("got %v", got)
	}
	if got := Place(paras, 0); got != nil {
		t.Fatal("no scenes")
	}
	// more scenes than paragraphs: stops when all taken
	if got := Place(paras, 6); len(got) != 4 {
		t.Fatalf("got %v", got)
	}
}

// Golden: reproduce build.py's placement for all ten Hobbit chapters.
func TestHobbitGolden(t *testing.T) {
	var chapters []Chapter
	data, err := os.ReadFile("testdata/hobbit-chapters.json")
	if err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal(data, &chapters); err != nil {
		t.Fatal(err)
	}
	var golden map[string]struct {
		Figures []int `json:"figures"`
		Paras   int   `json:"paras"`
	}
	data, _ = os.ReadFile("testdata/hobbit-placement.json")
	if err := json.Unmarshal(data, &golden); err != nil {
		t.Fatal(err)
	}
	for i, ch := range chapters {
		g := golden[string(rune('0'+i+1))]
		if i+1 == 10 {
			g = golden["10"]
		}
		paras := SplitParas(ch.Paras)
		if len(paras) != g.Paras {
			t.Errorf("ch %d: %d paragraphs after split, build.py had %d", i+1, len(paras), g.Paras)
			continue
		}
		got := Place(paras, len(g.Figures))
		if !reflect.DeepEqual(got, g.Figures) {
			t.Errorf("ch %d placement:\n got %v\nwant %v", i+1, got, g.Figures)
		}
	}
}

func TestLoadTiny(t *testing.T) {
	b, err := Load("../../testdata/content/books/tiny", "book.json", "scenes.json")
	if err != nil {
		t.Fatal(err)
	}
	if len(b.Chapters) != 2 || len(b.Scenes) != 2 || b.FigureOffset(1) != 2 {
		t.Fatalf("%+v", b)
	}
	if !IsVerse(b.Chapters[0].Paras[1]) {
		t.Fatal("verse detection")
	}
}

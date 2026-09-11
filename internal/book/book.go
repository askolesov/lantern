// Package book renders a book package: paragraph splitting and picture
// placement ported one-to-one from the Hobbit reader's build.py.
package book

import (
	"encoding/json"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"unicode/utf8"
)

type Chapter struct {
	Num   string   `json:"num"`
	Title string   `json:"title"`
	Paras []string `json:"paras"`
}

type Scene struct {
	Img     string `json:"img"`
	Caption string `json:"caption"`
}

// Book is a loaded package: chapters with already-split paragraphs and one
// ordered scene list per chapter.
type Book struct {
	Chapters []Chapter
	Scenes   [][]Scene
}

const splitLimit = 900

// sentence boundary: punctuation followed by whitespace (build.py: (?<=[.!?…»])\s+)
var sentEnd = regexp.MustCompile(`[.!?…»]\s+`)

// SplitLong splits a paragraph longer than limit characters at sentence
// boundaries, packing sentences greedily. Paragraphs containing a newline
// (verse) are never split.
func SplitLong(p string, limit int) []string {
	if utf8.RuneCountInString(p) <= limit || strings.Contains(p, "\n") {
		return []string{p}
	}
	var sents []string
	last := 0
	for _, m := range sentEnd.FindAllStringIndex(p, -1) {
		// split after the punctuation rune, drop the whitespace
		_, w := utf8.DecodeRuneInString(p[m[0]:])
		sents = append(sents, p[last:m[0]+w])
		last = m[1]
	}
	sents = append(sents, p[last:])
	var out []string
	cur := ""
	for _, sn := range sents {
		if cur != "" && utf8.RuneCountInString(cur)+utf8.RuneCountInString(sn) > limit {
			out = append(out, cur)
			cur = sn
		} else {
			cur = strings.TrimSpace(cur + " " + sn)
		}
	}
	if cur != "" {
		out = append(out, cur)
	}
	return out
}

// SplitParas applies SplitLong to every paragraph.
func SplitParas(paras []string) []string {
	var out []string
	for _, p := range paras {
		out = append(out, SplitLong(p, splitLimit)...)
	}
	return out
}

// Place spreads n scenes over the paragraphs by character count. It returns,
// for each scene in order, the index of the paragraph the picture goes
// before. First picture at the top, the last about half a step before the
// end; each paragraph takes at most one picture.
func Place(paras []string, n int) []int {
	if n <= 0 || len(paras) == 0 {
		return nil
	}
	cums := make([]float64, len(paras))
	total := 0.0
	for i, p := range paras {
		cums[i] = total
		total += float64(utf8.RuneCountInString(p))
	}
	step := total / (float64(n) - 0.5)
	taken := make([]bool, len(paras))
	out := make([]int, 0, n)
	for k := 0; k < n; k++ {
		tgt := float64(k) * step
		best := -1
		for i := range cums {
			if taken[i] {
				continue
			}
			if best < 0 || abs(cums[i]-tgt) < abs(cums[best]-tgt) {
				best = i
			}
		}
		if best < 0 {
			break // more scenes than paragraphs
		}
		taken[best] = true
		out = append(out, best)
	}
	return out
}

func abs(x float64) float64 {
	if x < 0 {
		return -x
	}
	return x
}

// IsVerse mirrors build.py: a paragraph with a newline and under 600 chars.
func IsVerse(p string) bool {
	return strings.Contains(p, "\n") && utf8.RuneCountInString(p) < 600
}

// Load reads text and scenes JSON from a package directory and splits the
// paragraphs. Chapters without a scene list get an empty one.
func Load(dir, text, scenes string) (*Book, error) {
	var b Book
	data, err := os.ReadFile(filepath.Join(dir, filepath.FromSlash(text)))
	if err != nil {
		return nil, err
	}
	if err := json.Unmarshal(data, &b.Chapters); err != nil {
		return nil, err
	}
	data, err = os.ReadFile(filepath.Join(dir, filepath.FromSlash(scenes)))
	if err != nil {
		return nil, err
	}
	if err := json.Unmarshal(data, &b.Scenes); err != nil {
		return nil, err
	}
	for i := range b.Chapters {
		b.Chapters[i].Paras = SplitParas(b.Chapters[i].Paras)
	}
	for len(b.Scenes) < len(b.Chapters) {
		b.Scenes = append(b.Scenes, nil)
	}
	return &b, nil
}

// FigureOffset is the number of figures in chapters before index k; the
// left/right alternation counts across the whole book (build.py's global n).
func (b *Book) FigureOffset(k int) int {
	n := 0
	for i := 0; i < k && i < len(b.Scenes); i++ {
		n += len(b.Scenes[i])
	}
	return n
}

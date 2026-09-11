// Package story renders one illustrated text: paragraph splitting and
// picture placement ported one-to-one from the Hobbit reader's build.py.
package story

import (
	"encoding/json"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"unicode/utf8"
)

type Scene struct {
	Img     string `json:"img"`
	Caption string `json:"caption"`
}

// Story is a loaded package: already-split paragraphs and the ordered scenes.
type Story struct {
	Paras  []string
	Scenes []Scene
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

// Load reads text.json (["para", …]) and scenes.json ([{img, caption}, …])
// from a package directory and splits the paragraphs.
func Load(dir, text, scenes string) (*Story, error) {
	var st Story
	data, err := os.ReadFile(filepath.Join(dir, filepath.FromSlash(text)))
	if err != nil {
		return nil, err
	}
	var paras []string
	if err := json.Unmarshal(data, &paras); err != nil {
		return nil, err
	}
	st.Paras = SplitParas(paras)
	data, err = os.ReadFile(filepath.Join(dir, filepath.FromSlash(scenes)))
	if err != nil {
		return nil, err
	}
	if err := json.Unmarshal(data, &st.Scenes); err != nil {
		return nil, err
	}
	return &st, nil
}

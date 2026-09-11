// Package catalog scans a content directory into a tree of nodes.
//
// A node is a directory containing node.yaml. Everything is explicit: the
// type is declared in the file, children are sorted by natural order of
// their directory names, and the cover is cover.jpg|png|webp next to
// node.yaml. Broken nodes are reported as Problems and skipped.
package catalog

import (
	"errors"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"
)

type Type string

const (
	Collection Type = "collection"
	Audio      Type = "audio"
	Video      Type = "video"
	Book       Type = "book"
)

const NodeFile = "node.yaml"

var coverNames = []string{"cover.jpg", "cover.png", "cover.webp"}

// Node is one directory with a node.yaml.
type Node struct {
	Path   string // slash-separated, relative to the content root; "" for the root
	Dir    string // absolute directory
	Type   Type
	Title  string
	Hidden bool
	Cover  string // file name of the cover next to node.yaml, "" if missing

	// audio / video
	File   string
	Source string

	// book
	Text   string
	Scenes string
	Images string

	Parent   *Node
	Children []*Node // collection only; sorted; includes hidden nodes
}

// Problem is one validation failure found while scanning.
type Problem struct {
	Path string
	Msg  string
}

func (p Problem) String() string {
	if p.Path == "" {
		return "(root): " + p.Msg
	}
	return p.Path + ": " + p.Msg
}

// Tree is the result of a scan.
type Tree struct {
	Root     *Node
	Problems []Problem
	byPath   map[string]*Node
}

type rawNode struct {
	Type   string `yaml:"type"`
	Title  string `yaml:"title"`
	Hidden bool   `yaml:"hidden"`
	File   string `yaml:"file"`
	Source string `yaml:"source"`
	Text   string `yaml:"text"`
	Scenes string `yaml:"scenes"`
	Images string `yaml:"images"`
}

// Scan reads the tree under root. The root directory itself must be a
// collection node (it needs node.yaml; its cover is optional).
func Scan(root string) (*Tree, error) {
	abs, err := filepath.Abs(root)
	if err != nil {
		return nil, err
	}
	if st, err := os.Stat(abs); err != nil || !st.IsDir() {
		return nil, fmt.Errorf("content root %q is not a directory", root)
	}
	t := &Tree{byPath: map[string]*Node{}}
	n, probs := load(abs, "", nil)
	t.Problems = append(t.Problems, probs...)
	if n == nil {
		return t, errors.New("content root has no valid " + NodeFile)
	}
	if n.Type != Collection {
		t.Problems = append(t.Problems, Problem{"", "root must be a collection"})
		return t, errors.New("content root is not a collection")
	}
	t.Root = n
	t.walk(n)
	return t, nil
}

func (t *Tree) walk(n *Node) {
	t.byPath[n.Path] = n
	if n.Type != Collection {
		return
	}
	entries, err := os.ReadDir(n.Dir)
	if err != nil {
		t.Problems = append(t.Problems, Problem{n.Path, "cannot read directory: " + err.Error()})
		return
	}
	names := make([]string, 0, len(entries))
	for _, e := range entries {
		if !e.IsDir() || strings.HasPrefix(e.Name(), ".") {
			continue
		}
		if _, err := os.Stat(filepath.Join(n.Dir, e.Name(), NodeFile)); err != nil {
			continue // not a node (src/, scratch, …)
		}
		names = append(names, e.Name())
	}
	sort.Slice(names, func(i, j int) bool { return natLess(names[i], names[j]) })
	for _, name := range names {
		child, probs := load(filepath.Join(n.Dir, name), path.Join(n.Path, name), n)
		t.Problems = append(t.Problems, probs...)
		if child == nil {
			continue
		}
		n.Children = append(n.Children, child)
		t.walk(child)
	}
}

// load parses one node directory. It returns nil when the node is unusable;
// cosmetic problems (missing cover) are reported but the node is kept.
func load(dir, rel string, parent *Node) (*Node, []Problem) {
	var probs []Problem
	fail := func(msg string) (*Node, []Problem) {
		return nil, append(probs, Problem{rel, msg})
	}
	data, err := os.ReadFile(filepath.Join(dir, NodeFile))
	if err != nil {
		return fail("missing " + NodeFile)
	}
	var raw rawNode
	if err := yaml.Unmarshal(data, &raw); err != nil {
		return fail("bad yaml: " + err.Error())
	}
	n := &Node{Path: rel, Dir: dir, Type: Type(raw.Type), Title: strings.TrimSpace(raw.Title),
		Hidden: raw.Hidden, Source: raw.Source, Parent: parent}
	if n.Title == "" {
		return fail("title is required")
	}
	inside := func(field, p string) (string, bool) {
		if p == "" {
			probs = append(probs, Problem{rel, field + " is required"})
			return "", false
		}
		clean := filepath.ToSlash(filepath.Clean(p))
		if path.IsAbs(clean) || clean == ".." || strings.HasPrefix(clean, "../") {
			probs = append(probs, Problem{rel, field + " escapes the node directory: " + p})
			return "", false
		}
		if _, err := os.Stat(filepath.Join(dir, filepath.FromSlash(clean))); err != nil {
			probs = append(probs, Problem{rel, field + " not found: " + p})
			return "", false
		}
		return clean, true
	}
	ok := true
	switch n.Type {
	case Collection:
	case Audio, Video:
		var o bool
		n.File, o = inside("file", raw.File)
		ok = ok && o
	case Book:
		var o1, o2, o3 bool
		n.Text, o1 = inside("text", raw.Text)
		n.Scenes, o2 = inside("scenes", raw.Scenes)
		n.Images, o3 = inside("images", raw.Images)
		ok = o1 && o2 && o3
	case "":
		return fail("type is required")
	default:
		return fail("unknown type " + raw.Type)
	}
	if !ok {
		return nil, probs
	}
	for _, c := range coverNames {
		if _, err := os.Stat(filepath.Join(dir, c)); err == nil {
			n.Cover = c
			break
		}
	}
	if n.Cover == "" && parent != nil {
		probs = append(probs, Problem{rel, "missing cover (cover.jpg|png|webp)"})
	}
	return n, probs
}

// Find returns the node at a slash-separated path, or nil.
func (t *Tree) Find(p string) *Node {
	return t.byPath[strings.Trim(p, "/")]
}

// Resolve splits a media path "<node path>/<file inside node>" at the longest
// node prefix. It returns the node and the file path relative to its
// directory, or nil when no node matches or the file escapes the node.
func (t *Tree) Resolve(p string) (*Node, string) {
	p = strings.Trim(p, "/")
	segs := strings.Split(p, "/")
	for i := len(segs); i >= 1; i-- { // i >= 1: the root serves no files
		n := t.byPath[strings.Join(segs[:i], "/")]
		if n == nil {
			continue
		}
		rest := strings.Join(segs[i:], "/")
		if rest == "" || rest == NodeFile {
			return nil, ""
		}
		clean := path.Clean(rest)
		if clean == ".." || strings.HasPrefix(clean, "../") || path.IsAbs(clean) {
			return nil, ""
		}
		return n, clean
	}
	return nil, ""
}

// Visible returns the children that are not hidden.
func (n *Node) Visible() []*Node {
	out := make([]*Node, 0, len(n.Children))
	for _, c := range n.Children {
		if !c.Hidden {
			out = append(out, c)
		}
	}
	return out
}

// Siblings returns the visible siblings of n (including n) in order, or
// just n when it is the root.
func (n *Node) Siblings() []*Node {
	if n.Parent == nil {
		return []*Node{n}
	}
	return n.Parent.Visible()
}

// PrevNext returns the visible neighbours of n in its collection.
func (n *Node) PrevNext() (prev, next *Node) {
	sib := n.Siblings()
	for i, s := range sib {
		if s == n {
			if i > 0 {
				prev = sib[i-1]
			}
			if i+1 < len(sib) {
				next = sib[i+1]
			}
		}
	}
	return
}

// IsLeaf reports whether the node is playable/readable content.
func (n *Node) IsLeaf() bool { return n.Type != Collection }


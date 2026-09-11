package catalog

import (
	"sort"
	"testing"
)

func TestNatLess(t *testing.T) {
	in := []string{"10", "2", "01-b", "01-a", "s1e10", "s1e9", "b", "A"}
	sort.Slice(in, func(i, j int) bool { return natLess(in[i], in[j]) })
	want := []string{"01-a", "01-b", "2", "10", "A", "b", "s1e9", "s1e10"}
	for i := range want {
		if in[i] != want[i] {
			t.Fatalf("got %v, want %v", in, want)
		}
	}
}

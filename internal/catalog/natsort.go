package catalog

import (
	"strings"
	"unicode"
)

// natLess compares two strings so that digit runs compare numerically:
// "2" < "10", "01-a" < "02-b", "s1e9" < "s1e10". Ties fall back to plain
// string comparison so the order is total and deterministic.
func natLess(a, b string) bool {
	ai, bi := 0, 0
	for ai < len(a) && bi < len(b) {
		ca, cb := a[ai], b[bi]
		if isDigit(ca) && isDigit(cb) {
			aj := ai
			for aj < len(a) && isDigit(a[aj]) {
				aj++
			}
			bj := bi
			for bj < len(b) && isDigit(b[bj]) {
				bj++
			}
			na := strings.TrimLeft(a[ai:aj], "0")
			nb := strings.TrimLeft(b[bi:bj], "0")
			if len(na) != len(nb) {
				return len(na) < len(nb)
			}
			if na != nb {
				return na < nb
			}
			ai, bi = aj, bj
			continue
		}
		ra, rb := unicode.ToLower(rune(ca)), unicode.ToLower(rune(cb))
		if ra != rb {
			return ra < rb
		}
		ai++
		bi++
	}
	if len(a)-ai != len(b)-bi {
		return len(a)-ai < len(b)-bi
	}
	return a < b
}

func isDigit(c byte) bool { return c >= '0' && c <= '9' }

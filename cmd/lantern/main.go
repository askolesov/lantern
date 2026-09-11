// Command lantern serves a content tree (serve) or validates one (check).
package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"

	"github.com/askolesov/lantern/internal/catalog"
	"github.com/askolesov/lantern/internal/web"
)

var version = "dev" // set by -ldflags at build time

func main() {
	if len(os.Args) < 2 {
		usage()
	}
	switch os.Args[1] {
	case "serve":
		fs := flag.NewFlagSet("serve", flag.ExitOnError)
		content := fs.String("content", "/content", "content root directory")
		addr := fs.String("addr", ":8080", "listen address")
		fs.Parse(os.Args[2:])
		if _, err := catalog.Scan(*content); err != nil {
			log.Fatalf("content: %v", err)
		}
		s, err := web.New(*content)
		if err != nil {
			log.Fatal(err)
		}
		log.Printf("lantern %s: serving %s on %s", version, *content, *addr)
		log.Fatal(http.ListenAndServe(*addr, s))
	case "check":
		if len(os.Args) < 3 {
			usage()
		}
		t, err := catalog.Scan(os.Args[2])
		if err != nil {
			fmt.Fprintln(os.Stderr, "error:", err)
		}
		blocking := 0
		for _, p := range t.Problems {
			fmt.Println(p)
			if !p.Hidden {
				blocking++
			}
		}
		n := 0
		var count func(*catalog.Node)
		count = func(x *catalog.Node) {
			n++
			for _, c := range x.Children {
				count(c)
			}
		}
		if t.Root != nil {
			count(t.Root)
		}
		fmt.Printf("%d nodes, %d problems (%d in hidden subtrees, not blocking)\n", n, len(t.Problems), len(t.Problems)-blocking)
		if err != nil || blocking > 0 {
			os.Exit(1)
		}
	default:
		usage()
	}
}

func usage() {
	fmt.Fprintln(os.Stderr, "usage: lantern serve [--content DIR] [--addr :8080] | lantern check DIR")
	os.Exit(2)
}

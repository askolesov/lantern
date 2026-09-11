CONTENT ?= $(HOME)/Documents/projects-my/lantern-content
NODE    ?= sidequest-k3s
REMOTE  ?= /srv/lantern/content
IMAGE   ?= ghcr.io/askolesov/lantern

.PHONY: build test run check sync image deploy fmt

build:
	go build -o lantern ./cmd/lantern

test:
	go vet ./... && go test ./...

fmt:
	gofmt -w cmd internal

run: build ## serve the local content dir on :8080
	./lantern serve --content $(CONTENT) --addr 127.0.0.1:8080

check: build ## validate the local content dir
	./lantern check $(CONTENT)

sync: check ## push content to the node (Mac is the master copy)
	rsync -av --delete --exclude '.DS_Store' --exclude '__pycache__' --exclude 'src/' --exclude '*.png' $(CONTENT)/ $(NODE):$(REMOTE)/

image: ## build the image locally (linux/amd64, like the cluster)
	docker build --platform linux/amd64 -f deploy/Dockerfile -t $(IMAGE):dev .

deploy: ## apply the k8s manifests (image tag pinned in deploy/k8s/kustomization.yaml)
	kubectl apply -k deploy/k8s
	kubectl -n lantern rollout status deploy/lantern

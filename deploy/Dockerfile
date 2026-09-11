# syntax=docker/dockerfile:1
FROM golang:1.26-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY cmd ./cmd
COPY internal ./internal
ARG VERSION=dev
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w -X main.version=${VERSION}" -o /lantern ./cmd/lantern

FROM scratch
COPY --from=build /lantern /lantern
VOLUME ["/content"]
EXPOSE 8080
USER 65534:65534
ENTRYPOINT ["/lantern"]
CMD ["serve", "--content", "/content", "--addr", ":8080"]

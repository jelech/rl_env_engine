# Multi-stage build for Go simulation server
# Final image < 30MB

FROM golang:1.21-alpine AS builder

RUN apk add --no-cache git

WORKDIR /app
COPY go/ ./go/
WORKDIR /app/go
RUN go mod download
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /server ./cmd/server

FROM alpine:3.19

RUN apk add --no-cache ca-certificates

COPY --from=builder /server /usr/local/bin/server

ENV GOGC=200

EXPOSE 9090

ENTRYPOINT ["server"]

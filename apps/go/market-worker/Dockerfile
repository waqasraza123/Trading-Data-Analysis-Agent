FROM golang:1.22-alpine AS build

WORKDIR /src/apps/go/market-worker
COPY apps/go/market-worker/go.mod ./
RUN go mod download
COPY apps/go/market-worker ./
RUN CGO_ENABLED=0 GOOS=linux go build -o /out/market-worker ./cmd/market-worker

FROM alpine:3.20

RUN addgroup -S marketworker && adduser -S marketworker -G marketworker
USER marketworker
WORKDIR /app
COPY --from=build /out/market-worker /app/market-worker
EXPOSE 8091
ENTRYPOINT ["/app/market-worker"]

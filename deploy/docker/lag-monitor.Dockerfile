FROM golang:1.27-alpine AS build
WORKDIR /src
COPY apps/lag-monitor/go.mod apps/lag-monitor/go.sum ./
RUN go mod download
COPY apps/lag-monitor/*.go ./
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /lag-monitor .

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /lag-monitor /lag-monitor
USER 65532:65532
EXPOSE 9308
ENTRYPOINT ["/lag-monitor"]

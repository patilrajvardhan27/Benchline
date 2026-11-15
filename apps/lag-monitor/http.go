package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
)

func routes(p *Poller) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		fmt.Fprintln(w, "ok")
	})
	mux.HandleFunc("GET /readyz", func(w http.ResponseWriter, _ *http.Request) {
		if !p.Ready(time.Now()) {
			http.Error(w, "no recent reading from Kafka", http.StatusServiceUnavailable)
			return
		}
		fmt.Fprintln(w, "ok")
	})
	mux.HandleFunc("GET /lag", func(w http.ResponseWriter, _ *http.Request) {
		snap, _ := p.Latest()
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(snap)
	})
	mux.HandleFunc("GET /metrics", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/plain; version=0.0.4")
		snap, errors := p.Latest()
		fmt.Fprint(w, metrics(snap, errors))
	})
	return mux
}

// metrics renders the Prometheus text format by hand; four series do not need a client library.
func metrics(snap Snapshot, errors int64) string {
	var b strings.Builder
	b.WriteString("# HELP benchline_consumer_lag Events a consumer group has not processed yet, per partition.\n")
	b.WriteString("# TYPE benchline_consumer_lag gauge\n")
	for _, g := range snap.Groups {
		for _, p := range g.Partitions {
			fmt.Fprintf(&b, "benchline_consumer_lag{group=%q,topic=%q,partition=\"%d\"} %d\n", g.Group, g.Topic, p.Partition, p.Lag)
		}
	}
	b.WriteString("# HELP benchline_consumer_lag_total Events a consumer group has not processed yet, all partitions.\n")
	b.WriteString("# TYPE benchline_consumer_lag_total gauge\n")
	for _, g := range snap.Groups {
		fmt.Fprintf(&b, "benchline_consumer_lag_total{group=%q,topic=%q} %d\n", g.Group, g.Topic, g.Total)
	}
	b.WriteString("# HELP benchline_lag_poll_errors_total Failed reads of Kafka offsets.\n")
	b.WriteString("# TYPE benchline_lag_poll_errors_total counter\n")
	fmt.Fprintf(&b, "benchline_lag_poll_errors_total %d\n", errors)
	if !snap.At.IsZero() {
		b.WriteString("# HELP benchline_lag_last_success_timestamp_seconds When offsets were last read.\n")
		b.WriteString("# TYPE benchline_lag_last_success_timestamp_seconds gauge\n")
		fmt.Fprintf(&b, "benchline_lag_last_success_timestamp_seconds %d\n", snap.At.Unix())
	}
	return b.String()
}

package main

import (
	"context"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/twmb/franz-go/pkg/kadm"
	"github.com/twmb/franz-go/pkg/kfake"
	"github.com/twmb/franz-go/pkg/kgo"
)

const topic = "pricing.price-point-recorded.v1"

// Against an in-memory Kafka: 5 events on partition 0, 3 on partition 1, none on partition 2.
// The worker has read 5 and 1, the ML service nothing.
func TestPollerAgainstKafka(t *testing.T) {
	cluster := kfake.MustCluster(kfake.NumBrokers(1), kfake.SeedTopics(3, topic))
	defer cluster.Close()
	client, err := kgo.NewClient(kgo.SeedBrokers(cluster.ListenAddrs()...), kgo.RecordPartitioner(kgo.ManualPartitioner()))
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()
	ctx := context.Background()

	for partition, count := range map[int32]int{0: 5, 1: 3} {
		for range count {
			r := &kgo.Record{Topic: topic, Partition: partition, Value: []byte(`{}`)}
			if err := client.ProduceSync(ctx, r).FirstErr(); err != nil {
				t.Fatal(err)
			}
		}
	}
	adm := kadm.NewClient(client)
	var commit kadm.Offsets
	commit.AddOffset(topic, 0, 5, -1)
	commit.AddOffset(topic, 1, 1, -1)
	if _, err := adm.CommitOffsets(ctx, "benchmark-worker", commit); err != nil {
		t.Fatal(err)
	}

	p := NewPoller(kafkaSource{adm: adm}, topic, []string{"benchmark-worker", "ml-anomaly"}, time.Second)
	if err := p.pollOnce(ctx); err != nil {
		t.Fatal(err)
	}
	snap, _ := p.Latest()
	if got := snap.Groups[0].Total; got != 2 {
		t.Fatalf("benchmark-worker lag = %d, want 2", got)
	}
	if got := snap.Groups[1].Total; got != 8 {
		t.Fatalf("ml-anomaly lag = %d, want 8", got)
	}

	body := get(t, routes(p), "/metrics", http.StatusOK)
	for _, line := range []string{
		`benchline_consumer_lag{group="benchmark-worker",topic="pricing.price-point-recorded.v1",partition="1"} 2`,
		`benchline_consumer_lag_total{group="ml-anomaly",topic="pricing.price-point-recorded.v1"} 8`,
		"benchline_lag_poll_errors_total 0",
	} {
		if !strings.Contains(body, line) {
			t.Errorf("metrics missing %q\n%s", line, body)
		}
	}
	get(t, routes(p), "/readyz", http.StatusOK)
}

type failingSource struct{}

func (failingSource) read(context.Context, string, []string) (offsets, error) {
	return offsets{}, errors.New("broker down")
}

func TestNotReadyUntilAReadSucceeds(t *testing.T) {
	p := NewPoller(failingSource{}, topic, []string{"benchmark-worker"}, time.Second)
	if err := p.pollOnce(context.Background()); err == nil {
		t.Fatal("expected an error")
	}
	h := routes(p)
	get(t, h, "/healthz", http.StatusOK)
	get(t, h, "/readyz", http.StatusServiceUnavailable)
	if body := get(t, h, "/metrics", http.StatusOK); !strings.Contains(body, "benchline_lag_poll_errors_total 1") {
		t.Fatalf("error not counted:\n%s", body)
	}
}

func TestStaleReadingIsNotReady(t *testing.T) {
	p := NewPoller(failingSource{}, topic, nil, time.Second)
	p.latest = Snapshot{At: time.Now().Add(-time.Minute)}
	if p.Ready(time.Now()) {
		t.Fatal("a minute-old reading with a 1s interval should not be ready")
	}
}

func get(t *testing.T, h http.Handler, path string, want int) string {
	t.Helper()
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, path, nil))
	body, _ := io.ReadAll(rec.Body)
	if rec.Code != want {
		t.Fatalf("GET %s = %d, want %d: %s", path, rec.Code, want, body)
	}
	return string(body)
}

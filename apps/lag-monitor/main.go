// lag-monitor reports how far Benchline's Kafka consumers are behind the price events.
package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/twmb/franz-go/pkg/kadm"
	"github.com/twmb/franz-go/pkg/kgo"
)

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, nil)))
	if err := run(); err != nil {
		slog.Error("lag-monitor stopped", "err", err)
		os.Exit(1)
	}
}

func run() error {
	interval, err := time.ParseDuration(env("LAG_INTERVAL", "15s"))
	if err != nil {
		return err
	}
	brokers := strings.Split(env("KAFKA_BOOTSTRAP", "localhost:9092"), ",")
	topic := env("LAG_TOPIC", "pricing.price-point-recorded.v1")
	groups := strings.Split(env("LAG_GROUPS", "benchmark-worker,ml-anomaly"), ",")

	client, err := kgo.NewClient(kgo.SeedBrokers(brokers...))
	if err != nil {
		return err
	}
	defer client.Close()

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	poller := NewPoller(kafkaSource{adm: kadm.NewClient(client)}, topic, groups, interval)
	go poller.Run(ctx)

	srv := &http.Server{
		Addr:              env("LISTEN_ADDR", ":9308"),
		Handler:           routes(poller),
		ReadHeaderTimeout: 5 * time.Second,
		WriteTimeout:      10 * time.Second,
	}
	go func() {
		<-ctx.Done()
		shutdown, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = srv.Shutdown(shutdown)
	}()
	slog.Info("lag-monitor listening", "addr", srv.Addr, "topic", topic, "groups", groups, "interval", interval)
	if err := srv.ListenAndServe(); !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return nil
}

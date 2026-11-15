package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"sync"
	"time"

	"github.com/twmb/franz-go/pkg/kadm"
	"github.com/twmb/franz-go/pkg/kerr"
)

// offsets is one reading of a topic and the groups that consume it.
type offsets struct {
	start, end map[int32]int64
	committed  map[string]map[int32]int64
}

type offsetSource interface {
	read(ctx context.Context, topic string, groups []string) (offsets, error)
}

type kafkaSource struct{ adm *kadm.Client }

func (s kafkaSource) read(ctx context.Context, topic string, groups []string) (offsets, error) {
	starts, err := s.adm.ListStartOffsets(ctx, topic)
	if err == nil {
		err = starts.Error()
	}
	if err != nil {
		return offsets{}, fmt.Errorf("start offsets: %w", err)
	}
	ends, err := s.adm.ListEndOffsets(ctx, topic)
	if err == nil {
		err = ends.Error()
	}
	if err != nil {
		return offsets{}, fmt.Errorf("end offsets: %w", err)
	}
	o := offsets{start: listed(starts[topic]), end: listed(ends[topic]), committed: map[string]map[int32]int64{}}
	for _, group := range groups {
		resp, err := s.adm.FetchOffsetsForTopics(ctx, group, topic)
		if err == nil {
			err = resp.Error()
		}
		committed := map[int32]int64{}
		if errors.Is(err, kerr.GroupIDNotFound) {
			o.committed[group] = committed // not started yet: everything is still to read
			continue
		}
		if err != nil {
			return offsets{}, fmt.Errorf("offsets for group %s: %w", group, err)
		}
		for partition, r := range resp[topic] {
			committed[partition] = r.At
		}
		o.committed[group] = committed
	}
	return o, nil
}

func listed(byPartition map[int32]kadm.ListedOffset) map[int32]int64 {
	out := make(map[int32]int64, len(byPartition))
	for partition, o := range byPartition {
		out[partition] = o.Offset
	}
	return out
}

// Snapshot is the latest successful reading.
type Snapshot struct {
	At     time.Time  `json:"at"`
	Groups []GroupLag `json:"groups"`
}

// Poller reads offsets on a timer and keeps the latest snapshot for the HTTP handlers.
type Poller struct {
	src      offsetSource
	topic    string
	groups   []string
	interval time.Duration

	mu     sync.RWMutex
	latest Snapshot
	errors int64
}

func NewPoller(src offsetSource, topic string, groups []string, interval time.Duration) *Poller {
	return &Poller{src: src, topic: topic, groups: groups, interval: interval}
}

func (p *Poller) Run(ctx context.Context) {
	ticker := time.NewTicker(p.interval)
	defer ticker.Stop()
	for {
		if err := p.pollOnce(ctx); err != nil && ctx.Err() == nil {
			slog.Warn("lag poll failed", "err", err)
		}
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
		}
	}
}

func (p *Poller) pollOnce(ctx context.Context) error {
	ctx, cancel := context.WithTimeout(ctx, p.interval)
	defer cancel()
	o, err := p.src.read(ctx, p.topic, p.groups)
	if err != nil {
		p.mu.Lock()
		p.errors++
		p.mu.Unlock()
		return err
	}
	snap := Snapshot{At: time.Now().UTC()}
	for _, group := range p.groups {
		snap.Groups = append(snap.Groups, computeLag(group, p.topic, o.start, o.end, o.committed[group]))
	}
	p.mu.Lock()
	p.latest = snap
	p.mu.Unlock()
	return nil
}

func (p *Poller) Latest() (Snapshot, int64) {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.latest, p.errors
}

// Ready is true when a poll succeeded recently; a stale reading should not be trusted.
func (p *Poller) Ready(now time.Time) bool {
	snap, _ := p.Latest()
	return !snap.At.IsZero() && now.Sub(snap.At) < 3*p.interval
}

package main

import "sort"

// PartitionLag is how far one consumer group is behind on one partition.
type PartitionLag struct {
	Partition int32 `json:"partition"`
	Committed int64 `json:"committed"` // -1 until the group commits on this partition
	End       int64 `json:"end"`
	Lag       int64 `json:"lag"`
}

// GroupLag is one consumer group's lag on one topic.
type GroupLag struct {
	Group      string         `json:"group"`
	Topic      string         `json:"topic"`
	Total      int64          `json:"total"`
	Partitions []PartitionLag `json:"partitions"`
}

// computeLag works out lag from the log start, log end and the group's committed offsets.
// A partition with no commit counts from the log start: both consumers use auto.offset.reset=earliest.
// A commit older than the log start (records deleted by retention) also counts from the log start.
func computeLag(group, topic string, start, end, committed map[int32]int64) GroupLag {
	out := GroupLag{Group: group, Topic: topic, Partitions: []PartitionLag{}}
	for partition, endOffset := range end {
		from := start[partition]
		at, ok := committed[partition]
		if !ok {
			at = -1
		}
		if at > from {
			from = at
		}
		lag := max(endOffset-from, 0)
		out.Partitions = append(out.Partitions, PartitionLag{Partition: partition, Committed: at, End: endOffset, Lag: lag})
		out.Total += lag
	}
	sort.Slice(out.Partitions, func(i, j int) bool { return out.Partitions[i].Partition < out.Partitions[j].Partition })
	return out
}

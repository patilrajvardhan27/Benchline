package main

import "testing"

func TestComputeLag(t *testing.T) {
	cases := []struct {
		name      string
		start     map[int32]int64
		end       map[int32]int64
		committed map[int32]int64
		want      []int64
		total     int64
	}{
		{"caught up", map[int32]int64{0: 0, 1: 0}, map[int32]int64{0: 5, 1: 3}, map[int32]int64{0: 5, 1: 3}, []int64{0, 0}, 0},
		{"behind", map[int32]int64{0: 0, 1: 0}, map[int32]int64{0: 5, 1: 3}, map[int32]int64{0: 2, 1: 3}, []int64{3, 0}, 3},
		{"never committed counts from log start", map[int32]int64{0: 2}, map[int32]int64{0: 9}, map[int32]int64{0: -1}, []int64{7}, 7},
		{"missing partition counts from log start", map[int32]int64{0: 0, 1: 4}, map[int32]int64{0: 1, 1: 6}, map[int32]int64{0: 1}, []int64{0, 2}, 2},
		{"commit before retention cut", map[int32]int64{0: 10}, map[int32]int64{0: 12}, map[int32]int64{0: 4}, []int64{2}, 2},
		{"empty topic", map[int32]int64{0: 0}, map[int32]int64{0: 0}, nil, []int64{0}, 0},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := computeLag("g", "t", c.start, c.end, c.committed)
			if got.Total != c.total {
				t.Fatalf("total = %d, want %d", got.Total, c.total)
			}
			for i, p := range got.Partitions {
				if p.Partition != int32(i) || p.Lag != c.want[i] {
					t.Fatalf("partition %d: got %+v, want lag %d", i, p, c.want[i])
				}
			}
		})
	}
}

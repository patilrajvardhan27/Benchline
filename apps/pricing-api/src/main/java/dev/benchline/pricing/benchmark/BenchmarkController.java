package dev.benchline.pricing.benchmark;

import dev.benchline.common.errors.ApiException;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/benchmarks/groups")
public class BenchmarkController {

    private final BenchmarkQueries queries;

    BenchmarkController(BenchmarkQueries queries) {
        this.queries = queries;
    }

    @GetMapping("/{groupId}")
    BenchmarkView latest(@PathVariable String groupId) {
        return queries.latest(groupId).orElseThrow(() -> ApiException.notFound("Benchmark for group", groupId));
    }

    @GetMapping("/{groupId}/history")
    BenchmarkHistory history(@PathVariable String groupId) {
        List<BenchmarkView> snapshots = queries.history(groupId);
        if (snapshots.isEmpty()) {
            throw ApiException.notFound("Benchmark for group", groupId);
        }
        return new BenchmarkHistory(groupId, snapshots);
    }
}

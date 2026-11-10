package dev.benchline.pricing.system;

import dev.benchline.common.flags.FeatureFlags;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1")
public class SystemController {

    private final OverviewQueries overview;
    private final FeatureFlags flags;

    SystemController(OverviewQueries overview, FeatureFlags flags) {
        this.overview = overview;
        this.flags = flags;
    }

    @GetMapping("/overview")
    Overview overview() {
        return overview.load();
    }

    @GetMapping("/config")
    FeatureConfig config() {
        return new FeatureConfig(flags.anomalyAlertsEnabled());
    }
}

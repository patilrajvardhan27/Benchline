package dev.benchline.pricing.insights;

import dev.benchline.common.errors.ApiException;
import dev.benchline.common.flags.FeatureFlags;
import dev.benchline.common.paging.PageMeta;
import dev.benchline.common.paging.PageParams;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Gated by the anomaly-alerts-enabled flag: when off, the queue looks empty. */
@RestController
@RequestMapping("/api/v1/anomalies")
public class AnomalyController {

    private final AnomalyQueries queries;
    private final FeatureFlags flags;

    AnomalyController(AnomalyQueries queries, FeatureFlags flags) {
        this.queries = queries;
        this.flags = flags;
    }

    @GetMapping
    AnomalyPage list(
            @RequestParam(required = false) AnomalyStatus status,
            @RequestParam(required = false) Integer page,
            @RequestParam(required = false) Integer size) {
        PageParams params = PageParams.of(page, size);
        if (!flags.anomalyAlertsEnabled()) {
            return new AnomalyPage(List.of(), PageMeta.of(params.page(), params.size(), 0));
        }
        return queries.list(status, params);
    }

    @PatchMapping("/{id}")
    AnomalyView review(@PathVariable UUID id, @Valid @RequestBody AnomalyReview body, Authentication auth) {
        if (body.status() == AnomalyStatus.OPEN) {
            throw ApiException.badRequest("status must be CONFIRMED or DISMISSED");
        }
        if (!queries.review(id, body.status(), auth.getName())) {
            throw ApiException.notFound("Anomaly", id.toString());
        }
        return queries.find(id).orElseThrow(() -> ApiException.notFound("Anomaly", id.toString()));
    }
}

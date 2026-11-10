package dev.benchline.pricing.pricing;

import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/** Write path. The benchmark updates later, when the event is consumed, hence 202. */
@RestController
@RequestMapping("/api/v1")
public class PriceController {

    private final PriceIngestService ingest;

    PriceController(PriceIngestService ingest) {
        this.ingest = ingest;
    }

    @PostMapping("/price-points")
    @ResponseStatus(HttpStatus.ACCEPTED)
    IngestReceipt record(@Valid @RequestBody PricePointInput input) {
        return ingest.ingest(List.of(input));
    }

    @PostMapping("/price-points:batch")
    @ResponseStatus(HttpStatus.ACCEPTED)
    IngestReceipt recordBatch(@Valid @RequestBody PricePointBatch batch) {
        return ingest.ingest(batch.pricePoints());
    }
}

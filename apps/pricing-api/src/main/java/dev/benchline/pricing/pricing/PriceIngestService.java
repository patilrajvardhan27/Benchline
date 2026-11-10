package dev.benchline.pricing.pricing;

import dev.benchline.common.errors.ApiException;
import dev.benchline.common.events.EventEnvelope;
import dev.benchline.common.events.PricePointRecorded;
import dev.benchline.common.money.Money;
import dev.benchline.common.outbox.OutboxPublisher;
import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Stores price points and queues one event per new row. A batch is one
 * transaction: either every row and its event are stored, or none are.
 */
@Service
public class PriceIngestService {

    private final JdbcClient jdbc;
    private final OutboxPublisher outbox;

    public PriceIngestService(JdbcClient jdbc, OutboxPublisher outbox) {
        this.jdbc = jdbc;
        this.outbox = outbox;
    }

    @Transactional
    public IngestReceipt ingest(List<PricePointInput> rows) {
        int accepted = 0;
        for (PricePointInput row : rows) {
            if (store(row)) {
                accepted++;
            }
        }
        return new IngestReceipt(accepted, rows.size() - accepted);
    }

    /** Returns false when the same item, source and effective date is already stored. */
    private boolean store(PricePointInput in) {
        if (in.source() == PriceSource.SYNTHETIC_DEMO) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "SYNTHETIC_DEMO prices cannot be written through the API");
        }
        String groupId = ItemGrouping.groupId(in.groupLabel());
        String itemId = ItemGrouping.itemId(in.ndc11());

        jdbc.sql("INSERT INTO catalog.item_group (id, name) VALUES (:id, :name) ON CONFLICT (id) DO NOTHING")
                .param("id", groupId)
                .param("name", ItemGrouping.normalizeName(in.groupLabel()))
                .update();
        jdbc.sql("""
                INSERT INTO catalog.item (id, ndc11, description, group_id, otc)
                VALUES (:id, :ndc, :description, :groupId, :otc) ON CONFLICT (id) DO NOTHING
                """)
                .param("id", itemId)
                .param("ndc", in.ndc11())
                .param("description", ItemGrouping.normalizeName(in.description()))
                .param("groupId", groupId)
                .param("otc", in.isOtc())
                .update();

        Optional<UUID> inserted = jdbc.sql("""
                INSERT INTO pricing.price_point
                    (item_id, source, unit_price, pricing_unit, effective_date, as_of_date)
                VALUES (:itemId, :source, :price, :unit, :effective, :asOf)
                ON CONFLICT (item_id, source, effective_date) DO NOTHING
                RETURNING id
                """)
                .param("itemId", itemId)
                .param("source", in.source().name())
                .param("price", Money.normalize(in.unitPrice()))
                .param("unit", in.pricingUnit())
                .param("effective", in.effectiveDate())
                .param("asOf", in.asOfDate())
                .query(UUID.class)
                .optional();
        if (inserted.isEmpty()) {
            return false;
        }

        PricePointRecorded payload = new PricePointRecorded(
                inserted.get(),
                itemId,
                groupId,
                in.source().name(),
                Money.normalize(in.unitPrice()),
                in.pricingUnit(),
                previousPrice(itemId, in),
                in.effectiveDate(),
                in.asOfDate());
        outbox.enqueue(groupId, EventEnvelope.of(PricePointRecorded.SOURCE, PricePointRecorded.TYPE, payload));
        return true;
    }

    private BigDecimal previousPrice(String itemId, PricePointInput in) {
        return jdbc.sql("""
                SELECT unit_price FROM pricing.price_point
                 WHERE item_id = :itemId AND source = :source AND effective_date < :effective
                 ORDER BY effective_date DESC LIMIT 1
                """)
                .param("itemId", itemId)
                .param("source", in.source().name())
                .param("effective", in.effectiveDate())
                .query(BigDecimal.class)
                .optional()
                .orElse(null);
    }
}

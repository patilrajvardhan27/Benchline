package dev.benchline.benchmark.support;

import dev.benchline.common.events.EventEnvelope;
import dev.benchline.common.events.PricePointRecorded;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;

/** Inserts catalog and price rows directly, the way the pricing API would have. */
public final class PriceData {

    public static final String GROUP = "grp-test-drug-10-mg-tab";

    private final JdbcClient jdbc;

    public PriceData(JdbcClient jdbc) {
        this.jdbc = jdbc;
        jdbc.sql("INSERT INTO catalog.item_group (id, name) VALUES (:id, 'TEST DRUG 10 MG TAB') ON CONFLICT DO NOTHING")
                .param("id", GROUP).update();
    }

    public void price(int n, String price, String effectiveDate) {
        String ndc = String.format("%011d", n);
        jdbc.sql("""
                INSERT INTO catalog.item (id, ndc11, description, group_id)
                VALUES (:id, :ndc, 'TEST DRUG 10 MG TAB', :group) ON CONFLICT DO NOTHING
                """).param("id", "ndc-" + ndc).param("ndc", ndc).param("group", GROUP).update();
        jdbc.sql("""
                INSERT INTO pricing.price_point (item_id, source, unit_price, pricing_unit, effective_date, as_of_date)
                VALUES (:item, 'NADAC', :price, 'EA', :eff, :eff)
                """)
                .param("item", "ndc-" + ndc).param("price", new BigDecimal(price))
                .param("eff", LocalDate.parse(effectiveDate)).update();
    }

    public static EventEnvelope<PricePointRecorded> event(String asOfDate) {
        PricePointRecorded data = new PricePointRecorded(
                UUID.randomUUID(), "ndc-00000000001", GROUP, "NADAC", new BigDecimal("0.1"), "EA", null,
                LocalDate.parse(asOfDate), LocalDate.parse(asOfDate));
        return EventEnvelope.of(PricePointRecorded.SOURCE, PricePointRecorded.TYPE, data);
    }
}

package dev.benchline.pricing.catalog;

import dev.benchline.common.errors.ApiException;
import dev.benchline.common.paging.PageParams;
import dev.benchline.pricing.pricing.PriceHistoryQueries;
import dev.benchline.pricing.pricing.PricePointView;
import java.time.LocalDate;
import java.util.List;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/items")
public class ItemController {

    private static final int MAX_QUERY_LENGTH = 100;

    private final ItemQueries items;
    private final PriceHistoryQueries history;

    ItemController(ItemQueries items, PriceHistoryQueries history) {
        this.items = items;
        this.history = history;
    }

    @GetMapping
    ItemPage search(
            @RequestParam(required = false) String query,
            @RequestParam(required = false) String group,
            @RequestParam(required = false) Integer page,
            @RequestParam(required = false) Integer size) {
        if (query != null && query.length() > MAX_QUERY_LENGTH) {
            throw ApiException.badRequest("query must be at most " + MAX_QUERY_LENGTH + " characters");
        }
        return items.search(query, group, PageParams.of(page, size));
    }

    @GetMapping("/{itemId}")
    ItemView get(@PathVariable String itemId) {
        return items.findById(itemId).orElseThrow(() -> ApiException.notFound("Item", itemId));
    }

    @GetMapping("/{itemId}/prices")
    List<PricePointView> prices(
            @PathVariable String itemId,
            @RequestParam(required = false) String source,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to) {
        requireItem(itemId);
        return history.forItem(itemId, source, from, to);
    }

    @GetMapping("/{itemId}/equivalents")
    List<Equivalent> equivalents(@PathVariable String itemId) {
        requireItem(itemId);
        return items.equivalents(itemId);
    }

    private void requireItem(String itemId) {
        if (items.findById(itemId).isEmpty()) {
            throw ApiException.notFound("Item", itemId);
        }
    }
}

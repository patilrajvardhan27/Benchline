package dev.benchline.pricing.member;

import dev.benchline.common.errors.ApiException;
import dev.benchline.common.paging.PageMeta;
import dev.benchline.common.paging.PageParams;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/members")
public class MemberController {

    private final MemberQueries queries;

    MemberController(MemberQueries queries) {
        this.queries = queries;
    }

    @GetMapping
    List<Facility> list() {
        return queries.facilities();
    }

    @GetMapping("/{memberId}/opportunities")
    OpportunityReport opportunities(
            @PathVariable String memberId,
            @RequestParam(required = false) Integer page,
            @RequestParam(required = false) Integer size) {
        Facility facility = queries.facility(memberId).orElseThrow(() -> ApiException.notFound("Member", memberId));
        PageParams params = PageParams.of(page, size);
        MemberQueries.Totals totals = queries.totals(memberId);
        return new OpportunityReport(
                facility,
                totals.savings(),
                queries.opportunities(memberId, params),
                PageMeta.of(params.page(), params.size(), totals.lines()));
    }
}

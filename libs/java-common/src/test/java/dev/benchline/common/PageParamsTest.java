package dev.benchline.common;

import static org.assertj.core.api.Assertions.assertThat;

import dev.benchline.common.paging.PageMeta;
import dev.benchline.common.paging.PageParams;
import org.junit.jupiter.api.Test;

class PageParamsTest {

    @Test
    void appliesDefaultsAndClamps() {
        assertThat(PageParams.of(null, null)).isEqualTo(new PageParams(0, 25));
        assertThat(PageParams.of(-4, 5000)).isEqualTo(new PageParams(0, 100));
        assertThat(PageParams.of(3, 0).size()).isEqualTo(1);
    }

    @Test
    void offsetIsPageTimesSize() {
        assertThat(PageParams.of(2, 10).offset()).isEqualTo(20);
    }

    @Test
    void totalPagesRoundsUp() {
        assertThat(PageMeta.of(0, 25, 51).totalPages()).isEqualTo(3);
        assertThat(PageMeta.of(0, 25, 0).totalPages()).isZero();
    }
}

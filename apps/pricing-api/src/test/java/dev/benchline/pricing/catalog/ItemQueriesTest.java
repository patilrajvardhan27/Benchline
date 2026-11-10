package dev.benchline.pricing.catalog;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class ItemQueriesTest {

    @Test
    void likeWildcardsTypedByUsersAreEscaped() {
        assertThat(ItemQueries.escapeLike("50%_off\\")).isEqualTo("50\\%\\_off\\\\");
    }

    @Test
    void plainTextIsUntouched() {
        assertThat(ItemQueries.escapeLike("atorvastatin 20")).isEqualTo("atorvastatin 20");
    }
}

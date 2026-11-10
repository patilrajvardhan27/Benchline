package dev.benchline.pricing.pricing;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class ItemGroupingTest {

    @Test
    void groupIdIsStableAcrossSpacingAndCase() {
        String a = ItemGrouping.groupId("ATORVASTATIN CALCIUM 20 MG TAB");
        String b = ItemGrouping.groupId("  atorvastatin   calcium 20 mg tab ");
        assertThat(a).isEqualTo(b).isEqualTo("grp-atorvastatin-calcium-20-mg-tab");
    }

    @Test
    void groupIdStripsPunctuation() {
        assertThat(ItemGrouping.groupId("12HR NASAL DECONGEST ER 120 MG (OTC)"))
                .isEqualTo("grp-12hr-nasal-decongest-er-120-mg-otc");
    }

    @Test
    void itemIdIsPrefixedNdc() {
        assertThat(ItemGrouping.itemId("00093715698")).isEqualTo("ndc-00093715698");
    }

    @Test
    void normalizeNameUppercasesAndCollapsesSpaces() {
        assertThat(ItemGrouping.normalizeName(" aspirin   81 mg ")).isEqualTo("ASPIRIN 81 MG");
    }
}

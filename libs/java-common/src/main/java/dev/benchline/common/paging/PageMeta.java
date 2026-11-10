package dev.benchline.common.paging;

/** Pagination block shared by every list response. */
public record PageMeta(int page, int size, long totalElements, int totalPages) {

    public static PageMeta of(int page, int size, long total) {
        int pages = size == 0 ? 0 : (int) Math.ceil((double) total / size);
        return new PageMeta(page, size, total, pages);
    }
}

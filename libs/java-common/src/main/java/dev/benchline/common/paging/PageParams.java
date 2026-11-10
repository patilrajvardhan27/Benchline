package dev.benchline.common.paging;

/** Validated page and size query parameters. */
public record PageParams(int page, int size) {

    public static final int DEFAULT_SIZE = 25;
    public static final int MAX_SIZE = 100;

    public static PageParams of(Integer page, Integer size) {
        int p = page == null ? 0 : Math.max(page, 0);
        int s = size == null ? DEFAULT_SIZE : Math.min(Math.max(size, 1), MAX_SIZE);
        return new PageParams(p, s);
    }

    public int offset() {
        return page * size;
    }
}

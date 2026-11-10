import type { PageMeta } from "../api/types";
import { formatInt } from "../format/format";

interface Props {
  page: PageMeta;
  onChange: (page: number) => void;
}

export function Pagination({ page, onChange }: Props) {
  if (page.totalPages <= 1) return null;
  const first = page.page * page.size + 1;
  const last = Math.min((page.page + 1) * page.size, page.totalElements);
  return (
    <nav className="pagination" aria-label="Pagination">
      <button type="button" className="btn btn--quiet" disabled={page.page === 0}
        onClick={() => { onChange(page.page - 1); }}>
        Previous
      </button>
      <span aria-live="polite">
        {formatInt(first)} to {formatInt(last)} of {formatInt(page.totalElements)}
      </span>
      <button type="button" className="btn btn--quiet" disabled={page.page + 1 >= page.totalPages}
        onClick={() => { onChange(page.page + 1); }}>
        Next
      </button>
    </nav>
  );
}

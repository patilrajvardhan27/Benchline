import { Link } from "react-router-dom";
import { PageShell } from "../shared/ui/PageShell";

export function NotFoundPage() {
  return (
    <PageShell title="Page not found">
      <p>That address does not match a page here.</p>
      <p><Link to="/">Go to the overview</Link> or <Link to="/items">search products</Link>.</p>
    </PageShell>
  );
}

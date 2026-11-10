import { type ReactNode, useEffect, useRef } from "react";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

interface Props {
  title: string;
  description?: string;
  /** Loading placeholders pass false so focus waits for the real page. */
  focusOnMount?: boolean;
  children: ReactNode;
}

// The first page of a visit keeps the browser's natural focus so the skip link is
// the first Tab stop. Every later page moves focus to its heading, which is how
// screen reader users learn that a client-side navigation happened.
let firstPageShown = false;

/** Wraps every page: sets the tab title, renders the h1 and plays the entrance animation. */
export function PageShell({ title, description, focusOnMount = true, children }: Props) {
  const heading = useRef<HTMLHeadingElement>(null);
  useDocumentTitle(title);

  useEffect(() => {
    if (!focusOnMount) return;
    if (firstPageShown) heading.current?.focus({ preventScroll: true });
    firstPageShown = true;
  }, [focusOnMount]);

  return (
    <div className="page-enter">
      <header className="page-head">
        <h1 tabIndex={-1} ref={heading}>{title}</h1>
        {description && <p>{description}</p>}
      </header>
      {children}
    </div>
  );
}

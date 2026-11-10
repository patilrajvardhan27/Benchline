import { Suspense, useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Footer } from "../shared/ui/Footer";
import { Header } from "../shared/ui/Header";
import { PageShell } from "../shared/ui/PageShell";
import { RouteProgress } from "../shared/ui/RouteProgress";
import { Skeleton } from "../shared/ui/Skeleton";

function Loading() {
  return (
    <PageShell title="Loading" focusOnMount={false}>
      <div aria-busy="true"><Skeleton variant="row" count={5} /></div>
    </PageShell>
  );
}

export function Layout() {
  const { pathname } = useLocation();
  // New page, new scroll position. Focus is handled by each page's heading (see PageShell).
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [pathname]);

  return (
    <div className="app">
      <a className="skip-link" href="#main">Skip to main content</a>
      <RouteProgress />
      <Header />
      <main id="main" tabIndex={-1}>
        <div className="container">
          <Suspense fallback={<Loading />}><Outlet /></Suspense>
        </div>
      </main>
      <Footer />
    </div>
  );
}

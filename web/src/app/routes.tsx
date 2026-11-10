import { lazy } from "react";
import { Route, Routes } from "react-router-dom";
import { PageShell } from "../shared/ui/PageShell";
import { Layout } from "./Layout";

// Each page is its own chunk so the first load stays small.
const page = <T extends string>(loader: () => Promise<Record<T, React.ComponentType>>, name: T) =>
  lazy(async () => ({ default: (await loader())[name] }));

const OverviewPage = page(() => import("../pages/OverviewPage"), "OverviewPage");
const ItemsPage = page(() => import("../pages/ItemsPage"), "ItemsPage");
const ItemDetailPage = page(() => import("../pages/ItemDetailPage"), "ItemDetailPage");
const OpportunitiesPage = page(() => import("../pages/OpportunitiesPage"), "OpportunitiesPage");
const AnomaliesPage = page(() => import("../pages/AnomaliesPage"), "AnomaliesPage");
const AboutPage = page(() => import("../pages/AboutPage"), "AboutPage");
const TermsPage = page(() => import("../pages/TermsPage"), "TermsPage");
const PrivacyPage = page(() => import("../pages/PrivacyPage"), "PrivacyPage");
const LegalNoticePage = page(() => import("../pages/LegalNoticePage"), "LegalNoticePage");
const AccessibilityPage = page(() => import("../pages/AccessibilityPage"), "AccessibilityPage");
const ContactPage = page(() => import("../pages/ContactPage"), "ContactPage");
const NotFoundPage = page(() => import("../pages/NotFoundPage"), "NotFoundPage");

function SigningIn() {
  return <PageShell title="Signing you in"><p>One moment.</p></PageShell>;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<OverviewPage />} />
        <Route path="items" element={<ItemsPage />} />
        <Route path="items/:itemId" element={<ItemDetailPage />} />
        <Route path="opportunities" element={<OpportunitiesPage />} />
        <Route path="anomalies" element={<AnomaliesPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="terms" element={<TermsPage />} />
        <Route path="privacy" element={<PrivacyPage />} />
        <Route path="legal" element={<LegalNoticePage />} />
        <Route path="accessibility" element={<AccessibilityPage />} />
        <Route path="contact" element={<ContactPage />} />
        <Route path="auth/callback" element={<SigningIn />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

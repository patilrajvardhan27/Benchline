import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import type { ReactElement } from "react";
import { Route, Routes } from "react-router-dom";
import { renderWithProviders } from "../test/render";
import { stubSnapshotFetch } from "../test/snapshot";
import { AboutPage } from "./AboutPage";
import { AccessibilityPage } from "./AccessibilityPage";
import { AnomaliesPage } from "./AnomaliesPage";
import { ContactPage } from "./ContactPage";
import { ItemDetailPage } from "./ItemDetailPage";
import { ItemsPage } from "./ItemsPage";
import { LegalNoticePage } from "./LegalNoticePage";
import { NotFoundPage } from "./NotFoundPage";
import { OpportunitiesPage } from "./OpportunitiesPage";
import { OverviewPage } from "./OverviewPage";
import { PrivacyPage } from "./PrivacyPage";
import { TermsPage } from "./TermsPage";

beforeEach(() => { stubSnapshotFetch(); });

const STATIC_PAGES: [string, ReactElement][] = [
  ["About", <AboutPage key="a" />],
  ["Terms of Service", <TermsPage key="t" />],
  ["Privacy Policy", <PrivacyPage key="p" />],
  ["Legal notice", <LegalNoticePage key="l" />],
  ["Accessibility statement", <AccessibilityPage key="x" />],
  ["Contact", <ContactPage key="c" />],
  ["Page not found", <NotFoundPage key="n" />],
];

describe.each(STATIC_PAGES)("%s", (title, page) => {
  it("has one h1 and no accessibility violations", async () => {
    const { container } = renderWithProviders(page);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(title);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("legal content", () => {
  it("links the operator contact and states non-affiliation", () => {
    renderWithProviders(<LegalNoticePage />);
    expect(screen.getAllByRole("link", { name: "hello@example.test" })[0]).toHaveAttribute("href", "mailto:hello@example.test");
    expect(screen.getByText(/not affiliated with, sponsored by or endorsed by Vizient/)).toBeInTheDocument();
  });

  it("privacy policy says no cookies are set", () => {
    renderWithProviders(<PrivacyPage />);
    expect(screen.getByText(/We set no cookies/)).toBeInTheDocument();
  });
});

describe("Contact form", () => {
  it("shows errors and does not compose an email when input is invalid", async () => {
    const onCompose = vi.fn();
    renderWithProviders(<ContactPage onCompose={onCompose} />);
    await userEvent.type(screen.getByLabelText("Your email"), "not-an-email");
    await userEvent.type(screen.getByLabelText("Message"), "short");
    await userEvent.click(screen.getByRole("button", { name: /open in my email app/i }));
    expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument();
    expect(screen.getByText("Write at least 10 characters.")).toBeInTheDocument();
    expect(screen.getByLabelText("Your email")).toHaveAttribute("aria-invalid", "true");
    expect(onCompose).not.toHaveBeenCalled();
  });

  it("builds an encoded mailto link when valid", async () => {
    const onCompose = vi.fn();
    renderWithProviders(<ContactPage onCompose={onCompose} />);
    await userEvent.selectOptions(screen.getByLabelText("What is this about?"), "bug");
    await userEvent.type(screen.getByLabelText("Your email"), "me@example.org");
    await userEvent.type(screen.getByLabelText("Message"), "The chart is missing & broken.");
    await userEvent.click(screen.getByRole("button", { name: /open in my email app/i }));
    expect(onCompose).toHaveBeenCalledTimes(1);
    const url = String(onCompose.mock.calls[0]?.[0]);
    expect(url.startsWith("mailto:hello@example.test?subject=Benchline%3A%20A%20bug")).toBe(true);
    expect(url).toContain("missing%20%26%20broken");
    expect(url).toContain("me%40example.org");
  });
});

describe("Overview", () => {
  it("shows live-looking stats from the API", async () => {
    const { container } = renderWithProviders(<OverviewPage />);
    expect(await screen.findByText("Products (NDCs)")).toBeInTheDocument();
    await waitFor(() => { expect(screen.getAllByText("3").length).toBeGreaterThan(0); });
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("Items", () => {
  it("lists products and filters by the search box", async () => {
    const { container } = renderWithProviders(<ItemsPage />);
    expect(await screen.findAllByRole("link", { name: /ATORVASTATIN/ })).toHaveLength(2);
    await userEvent.type(screen.getByLabelText("Search products"), "metformin");
    expect(await screen.findByRole("link", { name: /METFORMIN/ })).toBeInTheDocument();
    await waitFor(() => { expect(screen.queryByRole("link", { name: /ATORVASTATIN/ })).not.toBeInTheDocument(); });
    expect(await axe(container)).toHaveNoViolations();
  });

  it("says so when nothing matches", async () => {
    renderWithProviders(<ItemsPage />, "/items?q=zzzz");
    expect(await screen.findByText("No products found")).toBeInTheDocument();
  });
});

describe("Item detail", () => {
  const detail = (id: string) => renderWithProviders(
    <Routes><Route path="/items/:itemId" element={<ItemDetailPage />} /></Routes>, `/items/${id}`);

  it("shows price, benchmark, chart and equivalents", async () => {
    const { container } = detail("ndc-00000000001");
    expect(await screen.findByRole("heading", { level: 1, name: /ATORVASTATIN/ })).toBeInTheDocument();
    expect(await screen.findByRole("img", { name: /NADAC price per unit/ })).toBeInTheDocument();
    expect(await screen.findByRole("img", { name: /Benchmark range/ })).toBeInTheDocument();
    expect(await screen.findByText("Above group median")).toBeInTheDocument();
    const equivalents = await screen.findByRole("table", { name: /Lower-priced products/ });
    expect(within(equivalents).getByText("00000000002")).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it("shows a plain message for an unknown product", async () => {
    detail("ndc-99999999999");
    expect(await screen.findByRole("alert")).toHaveTextContent("We could not find what you asked for.");
  });
});

describe("Opportunities", () => {
  it("always labels the data as synthetic and totals the savings", async () => {
    const { container } = renderWithProviders(<OpportunitiesPage />);
    expect(screen.getByRole("note")).toHaveTextContent("Synthetic demo data");
    expect(await screen.findByText("$125.50")).toBeInTheDocument();
    expect(await screen.findByRole("table", { name: /Synthetic purchase lines/ })).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("Anomalies", () => {
  it("lists the queue and keeps review buttons off in demo mode", async () => {
    const { container } = renderWithProviders(<AnomaliesPage />);
    const table = await screen.findByRole("table", { name: /flagged as unusual/ });
    expect(within(table).getByText("6.2")).toBeInTheDocument();
    expect(within(table).getByRole("button", { name: /Confirm/ })).toBeDisabled();
    expect(screen.getByText(/Reviewing is turned off/)).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it("switches status tabs", async () => {
    renderWithProviders(<AnomaliesPage />);
    await screen.findByRole("table");
    await userEvent.click(screen.getByRole("button", { name: "Dismissed" }));
    expect(await screen.findByText("No dismissed anomalies")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dismissed" })).toHaveAttribute("aria-pressed", "true");
  });
});

import { Link } from "react-router-dom";
import { ContactEmail, LegalPage } from "../legal/LegalPage";

export function AccessibilityPage() {
  return (
    <LegalPage title="Accessibility statement">
      <h2>Our aim</h2>
      <p>
        Benchline aims to meet WCAG 2.2 level AA. We want the site to work with a keyboard, a screen
        reader, browser zoom and reduced motion.
      </p>

      <h2>What we do</h2>
      <ul>
        <li>Every page is checked with automated axe-core tests in continuous integration, and a build fails on any violation.</li>
        <li>All functions work from the keyboard, with a visible focus outline and a skip link.</li>
        <li>Charts have a text description and a matching data table.</li>
        <li>Text and controls meet AA colour contrast. Colour is never the only signal.</li>
        <li>Animation respects the "reduce motion" setting in your system.</li>
        <li>Moving to a new page puts focus on its heading so screen readers announce it.</li>
      </ul>

      <h2>Known limits</h2>
      <p>
        Automated tools find only part of the problems that exist. We have not yet had the site audited by
        people who use assistive technology every day. Product descriptions come straight from public
        data and are written in capitals with abbreviations.
      </p>

      <h2>Tell us about a problem</h2>
      <p>
        Email <ContactEmail /> or use the <Link to="/contact">Contact</Link> page. Say which page, what
        you were trying to do and what assistive technology you use. We aim to reply within five working days.
      </p>
    </LegalPage>
  );
}

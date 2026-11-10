import { Link } from "react-router-dom";
import { ContactEmail, LegalPage, Operator } from "../legal/LegalPage";

export function TermsPage() {
  return (
    <LegalPage title="Terms of Service">
      <h2>1. Who we are</h2>
      <p>
        Benchline is an independent portfolio project run by <Operator />, called "we" below. It is not
        a company product and is not affiliated with or endorsed by Vizient, Inc. or any other
        organization named on this site.
      </p>

      <h2>2. Agreeing to these terms</h2>
      <p>
        By using this website or its API you agree to these terms. If you do not agree, do not use the
        service. You must be old enough to form a binding agreement where you live.
      </p>

      <h2>3. Information only</h2>
      <p>
        Benchline shows public price data and statistics calculated from it. It is not purchasing,
        financial, clinical or legal advice. Do not set prices, negotiate contracts or make medication
        decisions from this site alone. Check the original source and ask a qualified person.
      </p>

      <h2>4. Where the data comes from</h2>
      <p>
        Prices come from the CMS National Average Drug Acquisition Cost (NADAC) survey, a market
        reference for what retail pharmacies pay. It is not the contract price any hospital or group
        purchasing organization pays. Benchmarks, groups and anomaly flags are our own calculations and
        can be wrong. Details are on the <Link to="/about">About</Link> page.
      </p>

      <h2>5. Synthetic data</h2>
      <p>
        Facilities and purchase lines are generated for demonstration and are labelled "synthetic". They
        do not describe real organizations or real purchases, and must not be presented as if they did.
      </p>

      <h2>6. Acceptable use</h2>
      <ul>
        <li>Do not attack, overload or probe the service for weaknesses without our written permission.</li>
        <li>Do not use automated tools in a way that harms availability for others. We may rate limit.</li>
        <li>Do not try to access data or functions you have not been given access to.</li>
        <li>Do not use the service to break the law or the rights of others.</li>
      </ul>
      <p>To report a security problem, see the <Link to="/contact">Contact</Link> page.</p>

      <h2>7. Accounts</h2>
      <p>
        Some deployments ask you to sign in through an identity provider. Keep your credentials safe. You
        are responsible for activity under your account. We may suspend access that breaks these terms.
      </p>

      <h2>8. Ownership and licenses</h2>
      <p>
        The Benchline source code is released under the MIT License. Public data keeps the terms of its
        publisher; see the <Link to="/legal">Legal notice</Link>. Names and logos of other organizations
        belong to them.
      </p>

      <h2>9. No guarantee of availability</h2>
      <p>
        The service is provided without a service level. It may be slow, change, or be switched off at
        any time, for example to stop cloud costs.
      </p>

      <h2>10. No warranty</h2>
      <p>
        The service is provided "as is" and "as available". To the fullest extent the law allows, we give
        no warranty of any kind, including accuracy, completeness, fitness for a purpose or
        non-infringement.
      </p>

      <h2>11. Limit of liability</h2>
      <p>
        To the fullest extent the law allows, we are not liable for indirect, incidental, special or
        consequential loss, or for loss of profit, data or business, arising from your use of or
        inability to use the service. Nothing here limits liability that cannot be limited by law.
      </p>

      <h2>12. Changes and ending</h2>
      <p>
        We may update these terms. The date at the top shows the latest version, and continued use after a
        change means you accept it. We may suspend or end the service, or your access, at any time.
      </p>

      <h2>13. Governing law</h2>
      <p>
        These terms are governed by the laws of the place where the operator is based, without regard to
        conflict-of-law rules. Courts there have jurisdiction, unless mandatory consumer law gives you a
        right to use your local courts.
      </p>

      <h2>14. Contact</h2>
      <p>Questions about these terms: <ContactEmail />.</p>
    </LegalPage>
  );
}

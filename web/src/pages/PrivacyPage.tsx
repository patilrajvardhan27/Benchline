import { Link } from "react-router-dom";
import { ContactEmail, LegalPage, Operator } from "../legal/LegalPage";

export function PrivacyPage() {
  return (
    <LegalPage title="Privacy Policy">
      <h2>Short version</h2>
      <p>
        Benchline does not use cookies, advertising, analytics or tracking scripts, and does not ask you
        for personal information to browse. The price data shown is public and is not about individuals.
      </p>

      <h2>1. Who is responsible</h2>
      <p>The controller of personal data on this site is <Operator />. Contact: <ContactEmail />.</p>

      <h2>2. What we handle</h2>
      <dl>
        <dt>Server logs</dt>
        <dd>
          When you load a page or call the API, the hosting provider and our servers record technical
          details: IP address, time, requested address, response code and browser type. We use them to
          keep the service running and secure. Logs do not include request bodies or prices you submit.
        </dd>
        <dt>Sign-in (only where enabled)</dt>
        <dd>
          If a deployment offers sign-in, your identity provider handles your credentials. We receive an
          account identifier and the permissions on your token. The token stays in your browser's memory
          and is gone when you close or reload the page. If you review an anomaly, we record who did it
          and when.
        </dd>
        <dt>Contact messages</dt>
        <dd>
          The contact form does not send anything to our servers. It opens your own email app with a
          draft. What you then send us reaches us through your email provider and is used only to reply.
        </dd>
      </dl>

      <h2>3. Cookies and local storage</h2>
      <p>
        We set no cookies. The site does not write to local storage. During sign-in, your browser keeps
        a short-lived value in session storage that completes the login and is cleared when the tab closes.
      </p>

      <h2>4. Third parties</h2>
      <p>
        Fonts are served from this site, so your browser does not contact a font provider. The site is
        delivered by a hosting provider, and sign-in by an identity provider, who act as processors for
        those parts and have their own policies. The data pipelines may send public product descriptions
        (drug names and strengths) to a language model provider the operator chooses. No visitor data is
        sent. We do not sell personal data.
      </p>

      <h2>5. Why we handle it, and for how long</h2>
      <p>
        We rely on our legitimate interest in running and securing a public website, and on your consent
        when you email us. Server logs are kept for the period the hosting provider sets, usually days to
        a few weeks. Emails are kept as long as needed to answer you, then deleted.
      </p>

      <h2>6. Your rights</h2>
      <p>
        Depending on where you live, you can ask to see, correct, delete or export personal data we hold
        about you, object to how we use it, or complain to your data protection authority. Email{" "}
        <ContactEmail /> and we will answer within one month.
      </p>

      <h2>7. Children</h2>
      <p>The service is not aimed at children under 16 and we do not knowingly collect their data.</p>

      <h2>8. Security</h2>
      <p>
        Traffic uses HTTPS, the API requires tokens for anything not public, and error messages hide
        internal detail. No system is perfectly secure. To report a weakness, use the{" "}
        <Link to="/contact">Contact</Link> page.
      </p>

      <h2>9. Changes</h2>
      <p>We will change this page when our practices change. The date at the top shows the latest version.</p>
    </LegalPage>
  );
}

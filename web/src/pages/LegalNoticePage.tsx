import { ContactEmail, LegalPage, Operator } from "../legal/LegalPage";

export function LegalNoticePage() {
  return (
    <LegalPage title="Legal notice">
      <h2>Operator</h2>
      <p>This site is run by <Operator /> as a personal, non-commercial project. Contact: <ContactEmail />.</p>

      <h2>No affiliation</h2>
      <p>
        Benchline is an independent portfolio project. It is not affiliated with, sponsored by or
        endorsed by Vizient, Inc., the Centers for Medicare &amp; Medicaid Services, the U.S. Department
        of Veterans Affairs or any other organization named here. All names and trademarks belong to
        their owners and appear only to say what the data is.
      </p>

      <h2>Data sources and licenses</h2>
      <div className="table-wrap" role="region" aria-label="Sources used by Benchline" tabIndex={0}>
        <table>
          <caption>Sources used by Benchline</caption>
          <thead><tr><th scope="col">Source</th><th scope="col">Use</th><th scope="col">Terms</th></tr></thead>
          <tbody>
            <tr><td>CMS NADAC (data.medicaid.gov)</td><td>Weekly drug acquisition costs</td><td>U.S. government public data</td></tr>
            <tr><td>IBM Plex fonts</td><td>Interface typefaces, served from this site</td><td>SIL Open Font License 1.1</td></tr>
            <tr><td>Benchline source code</td><td>This application</td><td>MIT License</td></tr>
          </tbody>
        </table>
      </div>

      <h2>Not advice</h2>
      <p>
        Nothing here is purchasing, financial, clinical or legal advice. NADAC is a survey of retail
        pharmacy acquisition costs and is not a hospital's contract price.
      </p>

      <h2>Accuracy and liability</h2>
      <p>
        We work to keep the data faithful to its sources, but we cannot promise it is complete, current
        or error-free. See the Terms of Service for the limits on our liability.
      </p>

      <h2>Synthetic data</h2>
      <p>Member facilities and purchase lines are generated and marked "synthetic". They are not real.</p>

      <h2>Copyright and takedown</h2>
      <p>
        If you believe something here infringes your rights, email <ContactEmail /> with enough detail to
        find it and we will look into it promptly.
      </p>

      <h2>Links</h2>
      <p>We are not responsible for the content of other websites we link to.</p>
    </LegalPage>
  );
}

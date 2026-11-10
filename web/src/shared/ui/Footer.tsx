import { Link } from "react-router-dom";
import { config } from "../config";

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="container">
        <nav aria-label="Legal and help">
          <ul>
            <li><Link to="/terms">Terms of Service</Link></li>
            <li><Link to="/privacy">Privacy Policy</Link></li>
            <li><Link to="/legal">Legal notice</Link></li>
            <li><Link to="/accessibility">Accessibility</Link></li>
            <li><Link to="/contact">Contact</Link></li>
          </ul>
        </nav>
        <p className="muted">
          Independent portfolio project. Not affiliated with or endorsed by Vizient, Inc.
        </p>
        <p className="muted">
          Prices come from public CMS NADAC data. Member purchase lines are synthetic demo data.
          {config.demoMode && " This site is showing a static snapshot."}
        </p>
      </div>
    </footer>
  );
}

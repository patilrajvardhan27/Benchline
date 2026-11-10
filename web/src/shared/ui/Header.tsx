import { Link, NavLink } from "react-router-dom";
import { useAuth } from "../api/auth";

const LINKS = [
  { to: "/", label: "Overview", end: true },
  { to: "/items", label: "Items" },
  { to: "/opportunities", label: "Opportunities" },
  { to: "/anomalies", label: "Anomalies" },
  { to: "/about", label: "About" },
];

export function Header() {
  const { status, signIn, signOut } = useAuth();
  return (
    <header className="site-header">
      <div className="container">
        <Link to="/" className="brand" aria-label="Benchline home">
          bench<span>line</span>
        </Link>
        <nav className="nav" aria-label="Main">
          {LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end}>{link.label}</NavLink>
          ))}
          {status === "anonymous" && (
            <button type="button" className="btn btn--quiet" onClick={() => void signIn()}>Sign in</button>
          )}
          {status === "authenticated" && (
            <button type="button" className="btn btn--quiet" onClick={() => void signOut()}>Sign out</button>
          )}
        </nav>
      </div>
    </header>
  );
}

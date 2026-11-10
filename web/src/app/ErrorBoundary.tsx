import { Component, type ReactNode } from "react";

interface State { failed: boolean }

/** Last line of defence: a rendering bug shows a calm message, never a stack trace. */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  override state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  override componentDidCatch() {
    // Details stay out of the page. A real deployment would report this to monitoring.
  }

  override render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="container" role="alert" style={{ padding: "var(--bl-space-12) var(--bl-space-4)" }}>
        <h1>Something went wrong</h1>
        <p>The page could not be shown. Reloading usually fixes it.</p>
        <button type="button" className="btn" onClick={() => { window.location.reload(); }}>Reload</button>
      </div>
    );
  }
}

import { Component, type ReactNode } from 'react';

export class RouteErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="route-status" role="alert">
          <h1>This page could not load</h1>
          <p>Check your connection, then reload to try again. Your selection link stays in the address bar.</p>
          <button className="btn btn--primary" onClick={() => window.location.reload()}>Reload page</button>
          <a className="btn btn--secondary" href="/">Back to home</a>
        </main>
      );
    }
    return this.props.children;
  }
}

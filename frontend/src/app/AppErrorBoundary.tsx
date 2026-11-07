import { Component } from "react";
import type { ErrorInfo, PropsWithChildren } from "react";

import { UnexpectedErrorPage } from "../features/errors/UnexpectedErrorPage";

interface AppErrorBoundaryState {
  hasError: boolean;
}

export class AppErrorBoundary extends Component<
  PropsWithChildren,
  AppErrorBoundaryState
> {
  state: AppErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): AppErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    if (import.meta.env.DEV) {
      console.error("Uncaught React error", error, info.componentStack);
    }
  }

  render() {
    if (this.state.hasError) {
      return <UnexpectedErrorPage />;
    }

    return this.props.children;
  }
}

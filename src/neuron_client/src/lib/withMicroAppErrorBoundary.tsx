import { ReactNode } from "react";
import { MicroAppErrorBoundary } from "../components/MicroAppErrorBoundary";

// Higher-order component wrapper for functional components
export function withMicroAppErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  fallback?: ReactNode,
  onReset?: () => void
) {
  return function WrappedComponent(props: P) {
    return (
      <MicroAppErrorBoundary fallback={fallback} onReset={onReset}>
        <Component {...props} />
      </MicroAppErrorBoundary>
    );
  };
}

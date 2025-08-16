import { Component, ErrorInfo, ReactNode } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

export class MicroAppErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("MicroApp Error Boundary caught an error:", error, errorInfo);

    this.setState({
      error,
      errorInfo,
    });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
    this.props.onReset?.();
  };

  public render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
      return (
        <div className="p-4 space-y-4">
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Micro App Error</AlertTitle>
            <AlertDescription>
              {this.isDisplaySchemaError()
                ? "There was an error rendering this micro app. This might be due to an invalid display configuration."
                : "Something went wrong while rendering this micro app."
              }
            </AlertDescription>
          </Alert>

          <div className="flex gap-2">
            <Button
              onClick={this.handleReset}
              variant="outline"
              size="sm"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
          </div>

          {process.env.NODE_ENV === "development" && this.state.error && (
            <details className="mt-4 p-2 bg-muted rounded text-sm">
              <summary className="cursor-pointer font-medium">
                Error Details (Development)
              </summary>
              <div className="mt-2 space-y-2">
                <div>
                  <strong>Error:</strong> {this.state.error.message}
                </div>
                <div>
                  <strong>Stack:</strong>
                  <pre className="mt-1 overflow-auto text-xs bg-background p-2 rounded">
                    {this.state.error.stack}
                  </pre>
                </div>
                {this.state.errorInfo && (
                  <div>
                    <strong>Component Stack:</strong>
                    <pre className="mt-1 overflow-auto text-xs bg-background p-2 rounded">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  </div>
                )}
              </div>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }

  private isDisplaySchemaError(): boolean {
    const errorMessage = this.state.error?.message || "";
    return (
      errorMessage.includes("Unknown component type") ||
      errorMessage.includes("Invalid field configuration") ||
      errorMessage.includes("display_schema") ||
      errorMessage.includes("component mapping")
    );
  }
}

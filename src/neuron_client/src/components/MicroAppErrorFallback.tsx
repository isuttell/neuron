import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface MicroAppErrorFallbackProps {
  error?: Error;
  onReset?: () => void;
}

export function MicroAppErrorFallback({
  error,
  onReset
}: MicroAppErrorFallbackProps) {
  return (
    <div className="p-4 border border-destructive/20 bg-destructive/5 rounded-lg">
      <div className="flex items-center gap-2 text-destructive mb-2">
        <AlertTriangle className="h-4 w-4" />
        <span className="font-medium">Component Error</span>
      </div>
      <p className="text-sm text-muted-foreground mb-3">
        This component failed to render. {error?.message}
      </p>
      {onReset && (
        <Button onClick={onReset} size="sm" variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      )}
    </div>
  );
}

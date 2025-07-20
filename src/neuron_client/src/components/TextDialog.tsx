import React, { ReactNode } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface TextDialogProps {
  children: ReactNode;
  trigger: ReactNode;
  title: string;
  actions?: ReactNode;
  metadata?: Record<string, unknown>;
  className?: string;
  icon?: LucideIcon;
}

const TextDialog: React.FC<TextDialogProps> = ({
  children,
  trigger,
  title,
  actions,
  metadata,
  className,
  icon: IconComponent,
}) => {
  return (
    <Dialog>
      <DialogTrigger asChild>
        {trigger}
      </DialogTrigger>
      <DialogContent
        className={cn(
          "max-w-4xl w-[95vw] max-h-[95vh] p-0 overflow-hidden",
          "sm:max-h-[90vh] sm:w-[90vw]",
          className
        )}
      >
        <div className="flex flex-col h-full max-h-[95vh] sm:max-h-[90vh] min-w-0">
          {/* Header */}
          <DialogHeader className="px-6 py-4 border-b shrink-0 text-left min-w-0 flex-shrink">
            <div className="flex items-center gap-3 min-w-0">
              {IconComponent && <IconComponent className="h-5 w-5 text-muted-foreground flex-shrink-0" />}
              <DialogTitle className="text-lg break-all min-w-0 max-w-full">{title}</DialogTitle>
            </div>
          </DialogHeader>

          {/* Action Toolbar - Mobile Only */}
          {actions && (
            <div className="flex items-center gap-2 border-b px-6 py-2 shrink-0 lg:hidden">
              {actions}
            </div>
          )}

          <div className="flex flex-col lg:flex-row flex-1 min-h-0">
            {/* Main Content */}
            <div className="flex-1 overflow-y-auto min-h-0">
              {children}
            </div>

            {/* Metadata Sidebar */}
            {(metadata && Object.keys(metadata).length > 0) || actions ? (
              <div className="lg:w-80 border-t lg:border-t-0 lg:border-l shrink-0">
                <div className="lg:overflow-y-auto lg:max-h-full">
                  <div className="space-y-4 px-6 py-4">
                    {/* Actions - Desktop Only */}
                    {actions && (
                      <div className="hidden lg:flex items-center gap-2 pb-4 border-b">
                        {actions}
                      </div>
                    )}

                    {metadata && Object.keys(metadata).length > 0 && (
                      <dl>
                        {Object.entries(metadata)
                          .filter(([, value]) => value !== null && value !== undefined && value !== '')
                          .map(([key, value]) => (
                            <div key={key} className="text-sm mb-4">
                              <dt className="font-medium text-muted-foreground capitalize mb-1">
                                {key.replace(/_/g, ' ')}
                              </dt>
                              <dd className="text-foreground break-words">
                                {typeof value === 'string' && value.startsWith('http') ? (
                                  <a
                                    href={value}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-primary hover:underline truncate block"
                                  >
                                    {value}
                                  </a>
                                ) : (
                                  String(value)
                                )}
                              </dd>
                            </div>
                          ))}
                      </dl>
                    )}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default TextDialog;

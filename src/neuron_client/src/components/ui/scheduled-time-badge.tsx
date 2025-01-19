import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { formatScheduledTime } from "@/lib/time";

interface ScheduledTimeBadgeProps {
  scheduledTime: string;
}

export function ScheduledTimeBadge({ scheduledTime }: ScheduledTimeBadgeProps) {
  const [formattedTime, setFormattedTime] = useState(() =>
    formatScheduledTime(scheduledTime)
  );

  useEffect(() => {
    // Update immediately when scheduledTime changes
    setFormattedTime(formatScheduledTime(scheduledTime));

    // Update every minute
    const interval = setInterval(() => {
      setFormattedTime(formatScheduledTime(scheduledTime));
    }, 10000);

    return () => clearInterval(interval);
  }, [scheduledTime]);

  return (
    <Badge variant="outline" className="text-sm text-muted-foreground">
      Runs {formattedTime}
    </Badge>
  );
}

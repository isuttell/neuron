export function formatScheduledTime(isoDate: string): string {
  const date = new Date(isoDate);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  // Format time
  const timeStr = date.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });

  // Today
  if (diffDays === 0) {
    if (diffMins < 60) {
      return diffMins <= 1 ? "in a minute" : `In ${diffMins} minutes`;
    }
    if (diffHours < 1) {
      return "today in " + diffMins + " minutes";
    }
    return `today at ${timeStr}`;
  }

  // Tomorrow
  if (diffDays === 1) {
    return `tomorrow at ${timeStr}`;
  }

  // Within a week
  if (diffDays < 7) {
    return `${date.toLocaleDateString("en-US", {
      weekday: "long",
    })} at ${timeStr}`;
  }

  // Within a month
  if (diffDays < 30) {
    return `${date.toLocaleDateString("en-US", {
      weekday: "long",
    })} the ${date.getDate()}${getOrdinalSuffix(date.getDate())} at ${timeStr}`;
  }

  // Beyond a month
  return (
    date.toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: now.getFullYear() !== date.getFullYear() ? "numeric" : undefined,
    }) + ` at ${timeStr}`
  );
}

function getOrdinalSuffix(day: number): string {
  if (day > 3 && day < 21) return "th";
  switch (day % 10) {
    case 1:
      return "st";
    case 2:
      return "nd";
    case 3:
      return "rd";
    default:
      return "th";
  }
}

export function formatRecurringPattern(interval: number, unit: string): string {
  if (interval === 1) {
    // For single intervals, return "every day", "every week", etc.
    return `every ${unit.slice(0, -1)}`;
  }
  // For multiple intervals, return "every 2 days", "every 3 weeks", etc.
  return `every ${interval} ${unit}`;
}

/**
 * Formats a number to a human-readable string with k/m suffixes
 * @param num The number to format
 * @returns Formatted string (e.g. "1.2k" or "1.5m")
 */
export function formatNumber(num: number, precision = 1): string {
  if (num >= 1_000_000) {
    return (num / 1_000_000).toFixed(precision) + "m";
  } else if (num >= 1_000) {
    return (num / 1_000).toFixed(precision) + "k";
  }
  return num.toString();
}

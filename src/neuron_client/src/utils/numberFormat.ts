/**
 * Formats a number to a human-readable string with k/m suffixes
 * @param num The number to format
 * @returns Formatted string (e.g. "1.2k" or "1.5m")
 */
export function formatNumber(num: number, precision = 1): string {
  // Handle special cases
  if (!isFinite(num)) {
    return num.toString();
  }

  const absNum = Math.abs(num);
  const sign = num < 0 ? "-" : "";

  if (absNum >= 1_000_000) {
    return sign + (absNum / 1_000_000).toFixed(precision) + "m";
  } else if (absNum >= 1_000) {
    return sign + (absNum / 1_000).toFixed(precision) + "k";
  }
  return num.toString();
}

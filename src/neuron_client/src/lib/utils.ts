import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Debounce a function
 * @param func - The function to debounce
 * @param wait - The wait time in milliseconds
 * @returns The debounced function
 */
export function debounce<Args extends unknown[], R>(
  func: (...args: Args) => R,
  wait: number
): (...args: Args) => void {
  let timeout: NodeJS.Timeout;
  return function (this: unknown, ...args: Args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

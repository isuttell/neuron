import { cn } from "@/lib/utils";
import { HTMLAttributes } from "react";

interface SpinnerProps extends HTMLAttributes<SVGElement> {
  className?: string;
  size?: number;
  strokeWidth?: number;
}

export function Spinner({
  className,
  size = 64,
  strokeWidth = 2,
  ...props
}: SpinnerProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn(`animate-spin`, className)}
      {...props}
    >
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

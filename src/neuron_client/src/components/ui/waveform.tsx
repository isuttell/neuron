export function Waveform({ className = "" }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M3 12h3" />
      <path d="M9 12h3" />
      <path d="M15 12h3" />
      <path d="M21 12h-3" />
      <path d="M6 9v6" />
      <path d="M12 6v12" />
      <path d="M18 9v6" />
    </svg>
  );
}

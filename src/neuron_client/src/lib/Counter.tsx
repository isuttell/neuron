import React, { useEffect, useState } from "react";

interface CounterProps {
  startDate: number;
  className?: string;
}

function formatTime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  const hoursDisplay = hours > 0 ? `${hours}h ` : "";
  const minutesDisplay = minutes > 0 ? `${minutes}m ` : "";
  const secondsDisplay = `${secs}s`;

  return `${hoursDisplay}${minutesDisplay}${secondsDisplay}`.trim();
}

const Counter: React.FC<CounterProps> = ({ startDate, className }) => {
  const [elapsedTime, setElapsedTime] = useState<number>(0);

  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date();
      const secondsElapsed = Math.floor(
        (now.getTime() - new Date(startDate).getTime()) / 1000
      );
      setElapsedTime(secondsElapsed);
    }, 1000);

    return () => clearInterval(interval);
  }, [startDate]);

  return <span className={className}>{formatTime(elapsedTime)}</span>;
};

export default Counter;

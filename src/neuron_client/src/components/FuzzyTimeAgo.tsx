import React, { useEffect, useState } from "react";

const getFuzzyTimeAgo = (date: number) => {
  const now = Date.now();
  const diff = now - date;

  // Convert to seconds and use fixed thresholds
  const seconds = Math.floor(diff / 1000);

  // Less than 1 minute
  if (seconds < 60) {
    return undefined;
  }

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m`;
  }

  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h`;
  }

  const days = Math.floor(hours / 24);
  if (days < 30) {
    return `${days}d`;
  }

  const months = Math.floor(days / 30);
  if (months < 12) {
    return `${months}mo`;
  }

  const years = Math.floor(days / 365);
  return `${years}y`;
};

interface FuzzyTimeAgoProps {
  timestamp: number;
  className?: string;
  ago?: boolean;
}

const FuzzyTimeAgo: React.FC<FuzzyTimeAgoProps> = ({
  timestamp,
  className,
  ago = false,
}) => {
  const [fuzzyTime, setFuzzyTime] = useState(getFuzzyTimeAgo(timestamp));

  useEffect(() => {
    const updateInterval = !fuzzyTime ? 1000 : 60000;
    const interval = setInterval(() => {
      setFuzzyTime(getFuzzyTimeAgo(timestamp));
    }, updateInterval);

    return () => clearInterval(interval);
  }, [timestamp, fuzzyTime]);

  return (
    <span className={className}>
      {fuzzyTime ? `${fuzzyTime}${ago ? " ago" : ""}` : "just now"}
    </span>
  );
};

export default FuzzyTimeAgo;

import React, { useEffect, useState } from "react";

const getFuzzyTimeAgo = (date: number) => {
  const now = new Date();

  const secondsPast = Math.floor((now.getTime() - date) / 1000);

  if (secondsPast < 60) {
    return undefined;
  }
  if (secondsPast < 3600) {
    return `${Math.floor(secondsPast / 60)}m`;
  }
  if (secondsPast <= 86400) {
    return `${Math.floor(secondsPast / 3600)}h`;
  }
  if (secondsPast <= 2592000) {
    return `${Math.floor(secondsPast / 86400)}d`;
  }
  if (secondsPast <= 31536000) {
    return `${Math.floor(secondsPast / 2592000)}mo`;
  }
  return `${Math.floor(secondsPast / 31536000)}y`;
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

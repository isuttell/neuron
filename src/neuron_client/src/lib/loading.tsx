import React from "react";
import { Spinner } from "@/components/ui/spinner";

interface LoadingProps {
  children?: React.ReactNode;
}

const Loading: React.FC<LoadingProps> = ({ children }) => {
  return (
    <div className="flex flex-1 items-center justify-center h-full">
      <div className="flex flex-col items-center gap-2">
        <Spinner />
        {children && <span>{children}</span>}
      </div>
    </div>
  );
};

export default Loading;

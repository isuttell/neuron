import React, { useState, useEffect } from "react";
import ArtifactItem from "./ArtifactItem";
import { Artifact } from "./extractArtifacts";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface ArtifactsViewerProps {
  artifacts: Artifact[];
}

const ArtifactsViewer: React.FC<ArtifactsViewerProps> = ({ artifacts }) => {
  const [activeKey, setActiveKey] = useState<string | null>(
    artifacts.length > 0 ? artifacts[artifacts.length - 1].key : null
  );
  const selectedArtifact = artifacts.find(({ key }) => key === activeKey);
  useEffect(() => {
    if (artifacts.length > 0) {
      setActiveKey(artifacts[artifacts.length - 1].key);
    }
  }, [artifacts.length]);
  return (
    <>
      <div className="flex flex-row gap-2">
        {artifacts.map(({ key, versions }, index) => (
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <Button
                key={key}
                onClick={() => setActiveKey(key)}
                className={cn(
                  activeKey === key
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground"
                )}
              >
                {index + 1}
              </Button>
            </TooltipTrigger>
            <TooltipContent className="max-w-[512px] p-4">
              {versions[0].title}
            </TooltipContent>
          </Tooltip>
        ))}
      </div>
      {selectedArtifact && (
        <ArtifactItem
          key={selectedArtifact.key}
          artifactVersions={selectedArtifact.versions}
        />
      )}
      {artifacts.length === 0 && (
        <div className="m-4 text-center text-muted-foreground">
          No artifacts found
        </div>
      )}
    </>
  );
};

export default ArtifactsViewer;

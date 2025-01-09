import React from "react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { Brain } from "lucide-react";
import { withAdminAuth } from "@/components/hoc/withAdminAuth";

interface EmbeddingsButtonProps {
  personalityId: string;
}

const EmbeddingsButton: React.FC<EmbeddingsButtonProps> = ({
  personalityId,
}) => {
  return (
    <Button variant="ghost" asChild size="icon">
      <Link
        className="text-foreground"
        to={`/personality/${personalityId}/embeddings`}
      >
        <Brain className="size-4" />
      </Link>
    </Button>
  );
};

export default withAdminAuth(EmbeddingsButton);

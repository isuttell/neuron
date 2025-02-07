import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { Brain } from "lucide-react";
import { withAdminAuth } from "@/components/hoc/withAdminAuth";

interface EmbeddingsButtonProps {
  personalityId: string;
}

export function EmbeddingsButtonComponent({
  personalityId,
}: EmbeddingsButtonProps) {
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
}

export const EmbeddingsButton = withAdminAuth(EmbeddingsButtonComponent);

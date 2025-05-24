import React, { useState } from "react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { ChevronDown, ChevronUp, FileText } from "lucide-react";
import { Citation } from "@/slices/messagesSlice";

interface CitationsProps {
  citations: Citation[];
}

const Citations: React.FC<CitationsProps> = ({ citations }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!citations || citations.length === 0) {
    return null;
  }

  // Group citations by document
  const citationsByDocument = citations.reduce((acc, citation) => {
    const key = citation.document_title;
    if (!acc[key]) {
      acc[key] = [];
    }
    acc[key].push(citation);
    return acc;
  }, {} as Record<string, Citation[]>);

  return (
    <Collapsible
      open={isOpen}
      onOpenChange={setIsOpen}
      className="mt-4 border rounded-lg bg-muted/30"
    >
      <CollapsibleTrigger asChild>
        <div className="flex items-center justify-between cursor-pointer px-4 py-3 hover:bg-muted/50 transition-colors">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">
              Citations ({citations.length})
            </span>
          </div>
          <button className="rounded-full p-1 hover:bg-muted">
            {isOpen ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </button>
        </div>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="px-4 pb-4 space-y-3">
          {Object.entries(citationsByDocument).map(([documentTitle, docCitations]) => (
            <Card key={documentTitle} className="p-3">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="text-xs">
                    {documentTitle}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {docCitations.length} citation{docCitations.length > 1 ? 's' : ''}
                  </span>
                </div>
                <div className="space-y-2 mt-2">
                  {docCitations.map((citation) => (
                    <div
                      key={`${citation.start_char_index}-${citation.end_char_index}`}
                      className="pl-4 border-l-2 border-muted"
                    >
                      <p className="text-sm text-muted-foreground italic">
                        "{citation.cited_text}"
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Characters {citation.start_char_index}-{citation.end_char_index}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
};

export default Citations;

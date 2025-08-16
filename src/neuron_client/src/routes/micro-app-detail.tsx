import { useParams } from "react-router-dom";
import { MicroAppDetailView } from "@/components/MicroAppDetailView";

export default function MicroAppDetailPage({ mode }: { mode: "view" | "edit" | "create" }) {
  const {appId, recordId} = useParams<{ appId: string; recordId: string }>();

  if (!appId) {
    return <div>App ID not provided</div>;
  }

  return (
    <MicroAppDetailView
      appId={appId}
      recordId={recordId}
      mode={mode}
    />
  );
}

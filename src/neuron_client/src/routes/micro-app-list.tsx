import { useParams } from "react-router-dom";
import { MicroAppListView } from "@/components/MicroAppListView";

export default function MicroAppListPage() {
  const { appId } = useParams<{ appId: string }>();

  if (!appId) {
    return <div>App ID not provided</div>;
  }

  return <MicroAppListView appId={appId} />;
}

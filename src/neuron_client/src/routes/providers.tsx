import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "../hooks";
import {
  fetchProviders,
  setupProvider,
  selectProviders,
  selectProvidersLoading,
  selectActiveProviderId,
} from "../slices/providerSlice";
import { Button } from "@/components/ui/button";
import { Settings } from "lucide-react";
import { useToast } from "../hooks/use-toast";
import { Badge } from "@/components/ui/badge";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import Loading from "@/lib/loading";

export default function ProvidersPage() {
  const dispatch = useAppDispatch();
  const { toast } = useToast();
  const providers = useAppSelector(selectProviders);
  const isLoading = useAppSelector(selectProvidersLoading);
  const activeProviderId = useAppSelector(selectActiveProviderId);

  useEffect(() => {
    dispatch(fetchProviders());
  }, []);

  const handleSetup = async (providerId: string) => {
    try {
      await dispatch(setupProvider(providerId)).unwrap();
      toast({
        title: "Provider setup successful",
      });
    } catch (error) {
      toast({
        title: "Failed to setup provider",
        variant: "destructive",
      });
    }
  };

  if (isLoading && providers.length === 0) {
    return <Loading />;
  }

  return (
    <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen overflow-auto">
      <div className="flex justify-between mb-2 border-b pb-2">
        <SidebarTrigger className="size-10 mr-2" />
        <h1 className="text-2xl font-bold">Providers</h1>
        <div className="flex-1" />
      </div>
      <ScrollArea className="flex-1 overflow-y-auto">
        <div className="space-y-4 max-w-[768px] mx-auto">
          {providers
            .sort((a, b) =>
              `${a.provider} ${a.model_id}`.localeCompare(
                `${b.provider} ${b.model_id}`
              )
            )
            .map((provider) => (
              <div
                key={provider.id}
                className="p-4 border rounded-lg flex justify-between items-start"
              >
                <div className="flex flex-col">
                  <div className="text-xl ml-2">{provider.model_id}</div>
                  <div>
                    <Badge variant="outline" className="capitalize">
                      {provider.provider}
                    </Badge>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant={
                          activeProviderId === provider.id
                            ? "default"
                            : "outline"
                        }
                        size="icon"
                        onClick={() => handleSetup(provider.id)}
                      >
                        <Settings className="h-4 w-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Setup provider</TooltipContent>
                  </Tooltip>
                </div>
              </div>
            ))}
          {providers.length === 0 && (
            <div className="p-4 flex justify-center items-center">
              <p className="text-sm text-gray-600">No providers available</p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

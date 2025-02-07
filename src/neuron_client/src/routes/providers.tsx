import { useEffect, useMemo } from "react";
import { useAppDispatch, useAppSelector } from "../hooks";
import {
  fetchProviders,
  setupProvider,
  selectProviders,
  selectProvidersLoading,
  selectActiveProviderId,
} from "../slices/providerSlice";
import { Button } from "@/components/ui/button";
import { Atom } from "lucide-react";
import { useToast } from "../hooks/use-toast";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import Loading from "@/lib/loading";

const PROVIDER_DISPLAY_NAMES: Record<string, string> = {
  anthropic: "Anthropic",
  cohere: "Cohere",
  openai: "OpenAI",
  openrouter: "OpenRouter",
};

export default function ProvidersPage() {
  const dispatch = useAppDispatch();
  const { toast } = useToast();
  const providers = useAppSelector(selectProviders);
  const isLoading = useAppSelector(selectProvidersLoading);
  const activeProviderId = useAppSelector(selectActiveProviderId);

  const groupedProviders = useMemo(() => {
    const groups = providers.reduce((acc, provider) => {
      const group = acc.get(provider.provider) || [];
      group.push(provider);
      acc.set(provider.provider, group);
      return acc;
    }, new Map<string, typeof providers>());

    // Convert to array and sort groups
    return Array.from(groups.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([provider, models]) => ({
        provider,
        models: models.sort((a, b) => a.model_id.localeCompare(b.model_id)),
      }));
  }, [providers]);

  useEffect(() => {
    dispatch(fetchProviders());
  }, [dispatch]);

  const handleSetup = async (providerId: string) => {
    try {
      await dispatch(setupProvider(providerId)).unwrap();
      toast({
        title: "Provider setup successful",
      });
    } catch {
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
          {groupedProviders.map(({ provider, models }) => (
            <div key={provider} className="space-y-2">
              <div className="text-xl font-semibold p-2">
                {PROVIDER_DISPLAY_NAMES[provider] || provider}
              </div>
              <div className="space-y-2">
                {models.map((model) => (
                  <div
                    key={model.id}
                    className="p-4 border rounded-lg flex justify-between items-start"
                  >
                    <div className="flex flex-col">
                      <div className="text-xl ml-2">{model.model_id}</div>
                    </div>
                    <div className="flex gap-2">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant={
                              activeProviderId === model.id
                                ? "default"
                                : "outline"
                            }
                            size="icon"
                            disabled={activeProviderId === model.id}
                            onClick={() => handleSetup(model.id)}
                          >
                            <Atom className="h-4 w-4" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Activate provider</TooltipContent>
                      </Tooltip>
                    </div>
                  </div>
                ))}
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

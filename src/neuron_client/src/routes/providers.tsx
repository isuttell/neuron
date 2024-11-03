import { useAppSelector, useAppDispatch } from "../hooks";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  getActiveProviderId,
  getProviders,
  ProviderModel,
  setActiveProvider,
} from "../slices/providersSlice";

import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function Providers() {
  const providers = useAppSelector(getProviders);
  const activeProviderId = useAppSelector(getActiveProviderId);

  const dispatch = useAppDispatch();
  const groupedProviders = providers.reduce((acc, provider) => {
    if (!acc[provider.provider]) {
      acc[provider.provider] = [];
    }
    acc[provider.provider].push(provider);
    return acc;
  }, {} as Record<string, ProviderModel[]>);
  return (
    <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen overflow-auto">
      <div className="flex justify-between mb-2 border-b pb-2">
        <h1 className="text-2xl font-bold">Providers</h1>
        <div className="flex-1" />
      </div>
      <ScrollArea className="flex-1 overflow-y-auto">
        <Select
          onValueChange={(providerId) => {
            const provider = providers.find((p) => p.id === providerId);
            if (provider) {
              dispatch(setActiveProvider({ provider }));
            }
          }}
          defaultValue={activeProviderId}
        >
          <SelectTrigger className="w-[350px]">
            <SelectValue placeholder="Select a provider" />
          </SelectTrigger>
          <SelectContent>
            {Object.keys(groupedProviders).map((provider) => (
              <SelectGroup key={provider}>
                <SelectLabel>{provider}</SelectLabel>
                {groupedProviders[provider].map((provider) => (
                  <SelectItem key={provider.id} value={provider.id}>
                    {provider.model_id}
                  </SelectItem>
                ))}
              </SelectGroup>
            ))}
          </SelectContent>
        </Select>
      </ScrollArea>
    </div>
  );
}

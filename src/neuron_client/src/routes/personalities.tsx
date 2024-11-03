import { useAppSelector } from "../hooks";
import { ScrollArea } from "@/components/ui/scroll-area";

import { getPersonalities } from "../slices/personalitiesSlice";
import PersonalityItem from "../personalities/PersonalityItem";
import EditUserDialog from "../personalities/EditPersonalityDialog";

export default function Personalities() {
  const personalities = useAppSelector(getPersonalities);

  return (
    <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen overflow-auto">
      <div className="flex justify-between mb-2 border-b pb-2">
        <h1 className="text-2xl font-bold">Personalities</h1>
        <div className="flex-1" />
        <EditUserDialog />
      </div>
      <ScrollArea className="flex-1 overflow-y-auto">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {personalities.map((personality) => (
            <PersonalityItem key={personality.id} personality={personality} />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}

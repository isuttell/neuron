import { ScrollArea } from "@/components/ui/scroll-area";

export default function Stats() {
  return (
    <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen overflow-auto">
      <div className="flex justify-between mb-2 border-b pb-2">
        <h1 className="text-2xl font-bold">Stats</h1>
        <div className="flex-1" />
      </div>
      <ScrollArea className="flex-1 overflow-y-auto">ts</ScrollArea>
    </div>
  );
}

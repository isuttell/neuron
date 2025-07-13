import { useEffect, useState, useMemo } from "react";
import { useAppSelector } from "../hooks";
import { ScrollArea } from "@/components/ui/scroll-area";
import { getPersonalities } from "../slices/personalitiesSlice";
import PersonalityItem from "../personalities/PersonalityItem";
import PersonalitySearch from "../personalities/PersonalitySearch";
import CreatePersonalityDialog from "../personalities/CreatePersonalityDialog";
import { useAppDispatch } from "../hooks";
import { fetchPersonalities } from "../actions/personalityActions";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  getPersonalitiesLoading,
  getPersonalitiesError,
} from "../slices/personalitiesSlice";
import { Spinner } from "@/components/ui/spinner";
import Fuse from "fuse.js";

export default function Personalities() {
  const personalities = useAppSelector(getPersonalities);
  const loading = useAppSelector(getPersonalitiesLoading);
  const error = useAppSelector(getPersonalitiesError);
  const dispatch = useAppDispatch();
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    dispatch(fetchPersonalities());
  }, [dispatch]);

  // Configure Fuse.js for fuzzy search
  const fuse = useMemo(() => {
    return new Fuse(personalities, {
      keys: ['name', 'description'],
      threshold: 0.3,
      includeScore: true,
    });
  }, [personalities]);

  // Filter and sort personalities based on search
  const filteredPersonalities = useMemo(() => {
    if (!searchTerm.trim()) {
      // No search term, return alphabetically sorted
      return personalities.slice().sort((a, b) => a.name.localeCompare(b.name));
    }

    // Search and return results sorted by relevance
    const results = fuse.search(searchTerm);
    return results.map(result => result.item);
  }, [personalities, searchTerm, fuse]);

  if (loading && personalities.length < 1) {
    return (
      <div className="flex items-center justify-center h-full w-full">
        <Spinner />
      </div>
    );
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  return (
    <div className="flex flex-1 p-4 ipad-top-spacing mobile-pwa-safe-top flex-col flex-nowrap max-h-screen overflow-auto">
      <div className="flex justify-between mb-2 border-b pb-2">
        <SidebarTrigger className="size-10 mr-2" />
        <h1 className="text-2xl font-bold">Personalities</h1>
        <div className="flex-1" />
        <CreatePersonalityDialog />
      </div>

      {/* Search Bar */}
      <div className="mb-4">
        <PersonalitySearch onSearch={setSearchTerm} />
      </div>

      <ScrollArea className="flex-1 overflow-y-auto">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filteredPersonalities.length > 0 ? (
            filteredPersonalities.map((personality) => (
              <PersonalityItem key={personality.id} personality={personality} />
            ))
          ) : (
            <div className="col-span-full text-center text-muted-foreground py-8">
              {searchTerm ? `No personalities found matching "${searchTerm}"` : "No personalities found"}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

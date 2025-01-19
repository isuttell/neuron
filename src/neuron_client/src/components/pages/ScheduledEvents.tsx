import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "@/hooks";
import { fetchEvents } from "@/slices/schedulerSlice";
import { ScheduledEvent } from "@/slices/schedulerSlice.d";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";
import { deleteEvent } from "@/slices/schedulerSlice";
import { RootState } from "@/store";
import Loading from "@/lib/loading";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { formatScheduledTime, formatRecurringPattern } from "@/lib/time";
import { Badge } from "@/components/ui/badge";
import Content from "@/messages/Content";
import { ScheduledTimeBadge } from "@/components/ui/scheduled-time-badge";

interface Personality {
  id: string;
  name: string;
}

export default function ScheduledEvents() {
  const dispatch = useAppDispatch();
  const { events, loading, error } = useAppSelector(
    (state: RootState) => state.scheduler
  );
  const personalities = useAppSelector(
    (state: RootState) => state.personalities.personalities
  );

  useEffect(() => {
    dispatch(fetchEvents());
  }, [dispatch]);

  // Group events by personality
  const eventsByPersonality = events.reduce(
    (acc: Record<string, ScheduledEvent[]>, event: ScheduledEvent) => {
      const personalityId = event.event_data.personality_id;
      if (!acc[personalityId]) {
        acc[personalityId] = [];
      }
      acc[personalityId].push(event);
      return acc;
    },
    {}
  );

  if (error) {
    return <div className="p-4 text-red-500">Error: {error}</div>;
  }

  if (loading) {
    return <Loading />;
  }

  const handleDeleteEvent = (eventId: string) => {
    dispatch(deleteEvent(eventId));
  };

  return (
    <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen overflow-auto">
      <div className="flex justify-between mb-2 border-b pb-2">
        <SidebarTrigger className="size-10 mr-2" />
        <h1 className="text-2xl font-bold">Scheduled</h1>
        <div className="flex-1" />
      </div>
      <ScrollArea className="flex-1 overflow-y-auto">
        <div className="space-y-8 max-w-[768px] mx-auto">
          {Object.entries(eventsByPersonality).map(
            ([personalityId, personalityEvents]) => {
              const personality = personalities.find(
                (p: Personality) => p.id === personalityId
              );
              return (
                <Card key={personalityId} className="mb-6">
                  <CardHeader>
                    <CardTitle className="text-xl flex">
                      {personality?.logo ? (
                        <img
                          src={personality?.logo?.replace(
                            /\.[^.]+$/,
                            `_t.webp`
                          )}
                          alt={personality?.name}
                          className="size-8 rounded-sm mr-4 max-w-8 max-h-8 overflow-hidden bg-muted"
                        />
                      ) : (
                        <div className="size-8 rounded-sm mr-4 max-w-8 max-h-8 bg-muted" />
                      )}
                      <h2 className="text-xl font-semibold ">
                        {personality?.name || "Unknown Personality"}
                      </h2>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {personalityEvents
                        .sort(
                          (a, b) =>
                            new Date(a.scheduled_time).getTime() -
                            new Date(b.scheduled_time).getTime()
                        )
                        .map((event: ScheduledEvent) => (
                          <div
                            key={event.event_id}
                            className="flex items-start p-4 border rounded-lg"
                          >
                            <div className="flex-1 space-y-2 max-w-full">
                              <Content
                                content={event.event_data.prompt}
                                className="mb-4 overflow-auto"
                              />
                              <div className="flex flex-row gap-2">
                                <ScheduledTimeBadge
                                  scheduledTime={event.scheduled_time}
                                />
                                {event.recurring_pattern && (
                                  <Badge
                                    variant="outline"
                                    className="text-sm text-muted-foreground"
                                  >
                                    Repeats{" "}
                                    {formatRecurringPattern(
                                      event.recurring_pattern.interval,
                                      event.recurring_pattern.unit
                                    )}
                                  </Badge>
                                )}
                              </div>
                            </div>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-red-500 hover:text-red-700 min-w-8"
                              onClick={() => handleDeleteEvent(event.event_id)}
                            >
                              <Trash2 className="size-8" />
                            </Button>
                          </div>
                        ))}
                    </div>
                  </CardContent>
                </Card>
              );
            }
          )}

          {events.length === 0 && (
            <div className="text-center text-muted-foreground">
              No scheduled events found
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

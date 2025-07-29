import { useAppSelector, useAppDispatch } from "../hooks";
import {
  getActivePersonalityId,
  getPersonalities,
  setActivePersonality,
} from "../slices/personalitiesSlice";
import { getConnectionStatus } from "../slices/socketSlice";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function PersonalitySelector() {
  const dispatch = useAppDispatch();
  const personalities = useAppSelector(getPersonalities);
  const activePersonalityId = useAppSelector(getActivePersonalityId);
  const personalitiesLoading = useAppSelector((state) => state.personalities.loading);
  const isConnected = useAppSelector(getConnectionStatus);

  const handlePersonalityChange = (personalityId: string) => {
    dispatch(setActivePersonality(personalityId));
  };

  return (
    <Select
      value={activePersonalityId || ""}
      onValueChange={handlePersonalityChange}
      disabled={personalitiesLoading || !isConnected}
    >
      <SelectTrigger className="w-[200px] h-8 text-sm">
        <SelectValue placeholder="Select personality" />
      </SelectTrigger>
      <SelectContent>
        {personalities.map((personality) => (
          <SelectItem key={personality.id} value={personality.id}>
            {personality.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

import { useAppSelector } from "../hooks";
import { getPersonalities } from "../slices/personalitiesSlice";
import { getConnectionStatus } from "../slices/socketSlice";
import { useNavigate, useParams } from "react-router-dom";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function PersonalitySelector() {
  const navigate = useNavigate();
  const { personalityId } = useParams();
  const personalities = useAppSelector(getPersonalities);
  const personalitiesLoading = useAppSelector((state) => state.personalities.loading);
  const isConnected = useAppSelector(getConnectionStatus);

  const handlePersonalityChange = (newPersonalityId: string) => {
    navigate(`/${newPersonalityId}`);
  };

  return (
    <Select
      value={personalityId || ""}
      onValueChange={handlePersonalityChange}
      disabled={personalitiesLoading || !isConnected}
    >
      <SelectTrigger className="w-[200px] h-8 text-sm">
        <SelectValue placeholder="Select personality" />
      </SelectTrigger>
      <SelectContent>
        {personalities
          .slice()
          .sort((a, b) => a.name.localeCompare(b.name))
          .map((personality) => (
            <SelectItem key={personality.id} value={personality.id}>
              {personality.name}
            </SelectItem>
          ))}
      </SelectContent>
    </Select>
  );
}

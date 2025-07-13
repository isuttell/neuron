import { useMemo } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useAppSelector } from "../hooks";
import { getProtectedToolSets } from "../slices/appSlice";
import { getUserRoles } from "../lib/auth";
import { ToolSetLabels, DEFAULT_TOOLSETS } from "../lib/toolsets";

interface ToolsetSelectorProps {
  value?: string[];
  defaultValue?: string[];
  onChange?: (value: string[]) => void;
  disabled?: boolean;
  className?: string;
}

export default function ToolsetSelector({
  value,
  defaultValue = DEFAULT_TOOLSETS,
  onChange,
  disabled = false,
  className = "",
}: ToolsetSelectorProps) {
  const { user } = useAuth0();
  const protectedToolSets = useAppSelector(getProtectedToolSets);

  // Filter tool sets based on user roles
  const availableToolSets = useMemo(() => {
    const userRoles = getUserRoles(user);
    const filteredLabels: Record<string, string> = {};

    Object.entries(ToolSetLabels).forEach(([key, label]) => {
      const requiredRole = protectedToolSets?.[key];
      if (!requiredRole || userRoles.includes(requiredRole)) {
        filteredLabels[key] = label;
      }
    });

    return filteredLabels;
  }, [user, protectedToolSets]);

  const activeTools = value && value.length > 0 ? value : defaultValue;

  const handleValueChange = (newValue: string[]) => {
    const filteredValue = newValue.filter(
      (val) => val !== "" && Object.keys(availableToolSets).includes(val)
    );
    onChange?.(filteredValue);
  };

  return (
    <div className={className}>
      <ToggleGroup
        className="flex-wrap gap-2 justify-start"
        type="multiple"
        variant="outline"
        value={activeTools}
        onValueChange={handleValueChange}
        disabled={disabled}
      >
        {Object.keys(availableToolSets).map((option) => (
          <ToggleGroupItem
            key={option}
            value={option}
            variant={defaultValue.includes(option) ? "default" : "outline"}
          >
            {availableToolSets[option]}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </div>
  );
}

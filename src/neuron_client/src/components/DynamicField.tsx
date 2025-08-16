import { useCallback, useMemo, useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { format } from "date-fns";
import { CalendarIcon } from "lucide-react";
import { MicroAppErrorFallback } from "./MicroAppErrorFallback";
import { useAppDispatch } from "../hooks";
import { updateRecordField } from "../slices/microAppsSlice";

interface FieldConfig {
  type: string;
  label?: string;
  placeholder?: string;
  required?: boolean;
  readonly?: boolean;
  options?: Array<{ value: string; label: string }>;
  props?: Record<string, unknown>;
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
    minLength?: number;
    maxLength?: number;
  };
}

interface DynamicFieldProps {
  name: string;
  config: FieldConfig;
  value: unknown;
  onChange?: (value: unknown) => void;
  onBlur?: () => void;
  error?: string;
  appId?: string;
  recordId?: string;
  optimisticUpdates?: boolean;
}

export function DynamicField({
  name,
  config,
  value,
  onChange,
  onBlur,
  error,
  appId,
  recordId,
  optimisticUpdates = false,
}: DynamicFieldProps) {
  const dispatch = useAppDispatch();

  // Local state for tracking raw user input (especially for number fields)
  const [rawInput, setRawInput] = useState<string>("");

  // Initialize rawInput when value changes from parent (useful for loading existing data)
  useEffect(() => {
    if (config.type === "number" && value !== undefined && value !== null && value !== "") {
      setRawInput(String(value));
    } else if (config.type === "number" && (value === "" || value === null || value === undefined)) {
      setRawInput("");
    }
  }, [config.type, value]);

  const handleChange = useCallback((newValue: unknown) => {
    // Call parent onChange if provided
    onChange?.(newValue);

    // Optimistic Redux update if enabled
    if (optimisticUpdates && appId && recordId) {
      dispatch(updateRecordField({
        appId,
        recordId,
        fieldName: name,
        value: newValue,
      }));
    }
  }, [onChange, optimisticUpdates, appId, recordId, name, dispatch]);

  const fieldId = `field-${name}`;
  const label = config.label || name;
  const isRequired = config.required || false;

  // Validation helpers
  const getValidationProps = useMemo(() => {
    if (!config.validation) return {};

    const props: Record<string, unknown> = {};
    if (config.validation.min !== undefined) props.min = config.validation.min;
    if (config.validation.max !== undefined) props.max = config.validation.max;
    if (config.validation.minLength !== undefined) props.minLength = config.validation.minLength;
    if (config.validation.maxLength !== undefined) props.maxLength = config.validation.maxLength;
    if (config.validation.pattern) props.pattern = config.validation.pattern;

    return props;
  }, [config.validation]);

  const renderField = () => {
    // Validate config before proceeding
    if (!config || typeof config !== 'object') {
      console.error(`Invalid field config for field '${name}':`, config);
      return (
        <MicroAppErrorFallback
          error={new Error(`Invalid field configuration for '${name}'`)}
          onReset={() => {
            return (
              <Input
                id={fieldId}
                value={String(value || "")}
                placeholder={`${label} (fallback)`}
                onChange={(e) => handleChange(e.target.value)}
                className="border-orange-300 bg-orange-50"
              />
            );
          }}
        />
      );
    }

    const commonProps = {
      id: fieldId,
      disabled: false,
      required: isRequired,
      ...config.props,
      ...getValidationProps,
    };

    try {
      switch (config.type) {
        case "input":
        case "text":
          return (
            <Input
              {...commonProps}
              type="text"
              value={String(value || "")}
              placeholder={config.placeholder}
              onChange={(e) => handleChange(e.target.value)}
              onBlur={onBlur}
              className={error ? "border-destructive" : ""}
            />
          );

        case "email":
          return (
            <Input
              {...commonProps}
              type="email"
              value={String(value || "")}
              placeholder={config.placeholder || "Enter email"}
              onChange={(e) => handleChange(e.target.value)}
              onBlur={onBlur}
              className={error ? "border-destructive" : ""}
            />
          );

        case "number":
          return (
            <Input
              {...commonProps}
              type="text"
              value={rawInput}
              placeholder={config.placeholder}
              onChange={(e) => {
                const inputValue = e.target.value;
                setRawInput(inputValue);

                // Always pass the raw input to let Zod handle validation and coercion
                handleChange(inputValue);
              }}
              onBlur={onBlur}
              className={error ? "border-destructive" : ""}
            />
          );

        case "textarea":
          return (
            <Textarea
              {...commonProps}
              value={String(value || "")}
              placeholder={config.placeholder}
              onChange={(e) => handleChange(e.target.value)}
              onBlur={onBlur}
              className={error ? "border-destructive" : ""}
            />
          );

        case "select":
          if (!config.options || !Array.isArray(config.options) || config.options.length === 0) {
            console.error(`Select field '${name}' has no valid options defined:`, config.options);
            return (
              <MicroAppErrorFallback
                error={new Error(`Select field '${name}' has no valid options defined`)}
                onReset={() => {
                  return (
                    <Input
                      id={fieldId}
                      value={String(value || "")}
                      placeholder={`${label} (fallback - options missing)`}
                      onChange={(e) => handleChange(e.target.value)}
                      className="border-orange-300 bg-orange-50"
                    />
                  );
                }}
              />
            );
          }

          // Validate option structure
          {
            const validOptions = config.options.filter(option => {
              return option && typeof option === 'object' &&
              typeof option.value === 'string' &&
              typeof option.label === 'string';
            });

          if (validOptions.length === 0) {
            console.error(`Select field '${name}' has no valid option objects:`, config.options);
            return (
              <MicroAppErrorFallback
                error={new Error(`Select field '${name}' has malformed options`)}
                onReset={() => {
                  return (
                    <Input
                      id={fieldId}
                      value={String(value || "")}
                      placeholder={`${label} (fallback - malformed options)`}
                      onChange={(e) => handleChange(e.target.value)}
                      className="border-orange-300 bg-orange-50"
                    />
                  );
                }}
              />
            );
          }

          return (
            <Select
              value={String(value || "")}
              onValueChange={handleChange}
              disabled={false}
              required={isRequired}
            >
              <SelectTrigger className={error ? "border-destructive" : ""}>
                <SelectValue placeholder={config.placeholder || "Select an option"} />
              </SelectTrigger>
              <SelectContent>
                {validOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          );
          }

        case "checkbox":
          return (
            <div className="flex items-center space-x-2">
              <Checkbox
                {...commonProps}
                checked={Boolean(value)}
                onCheckedChange={handleChange}
              />
              <Label
                htmlFor={fieldId}
                className="text-sm font-normal leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                {label}
              </Label>
            </div>
          );

        case "date": {
          const dateValue = value ? new Date(value as string) : undefined;

          return (
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={`w-full justify-start text-left font-normal ${
                    !dateValue && "text-muted-foreground"
                  } ${error ? "border-destructive" : ""}`}
                  disabled={false}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {dateValue ? format(dateValue, "PPP") : config.placeholder || "Pick a date"}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0">
                <Calendar
                  mode="single"
                  selected={dateValue}
                  onSelect={(date: Date | undefined) => handleChange(date?.toISOString())}
                  initialFocus
                />
              </PopoverContent>
            </Popover>
          );
        }

        case "array": {
          // Array input - treat as comma-separated text input for now
          const arrayValue = Array.isArray(value) ? value.join(", ") : String(value || "");

          return (
            <div className="space-y-2">
              <Input
                {...commonProps}
                type="text"
                value={arrayValue}
                placeholder={config.placeholder || "Enter values separated by commas"}
                onChange={(e) => handleChange(e.target.value)}
                onBlur={onBlur}
                className={error ? "border-destructive" : ""}
              />
              <p className="text-xs text-muted-foreground">
                Separate multiple values with commas
              </p>
            </div>
          );
        }

        default:
          throw new Error(`Unknown component type: ${config.type}`);
      }
    } catch (fieldError) {
      console.error(`Error rendering field '${name}':`, fieldError);
      return (
        <MicroAppErrorFallback
          error={fieldError as Error}
          onReset={() => {
            // Try to render as a basic input as fallback
            return (
              <Input
                id={fieldId}
                value={String(value || "")}
                placeholder={`${label} (fallback)`}
                onChange={(e) => handleChange(e.target.value)}
                className="border-orange-300 bg-orange-50"
              />
            );
          }}
        />
      );
    }
  };

  // Special handling for checkbox which includes its own label
  if (config.type === "checkbox") {
    return (
      <div className="space-y-2">
        {renderField()}
        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}
      </div>
    );
  }

  // Standard field with separate label
  return (
    <div className="space-y-2">
      <Label htmlFor={fieldId} className="text-sm font-medium">
        {label}
        {isRequired && <span className="text-destructive ml-1">*</span>}
      </Label>
      {renderField()}
      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}
    </div>
  );
}

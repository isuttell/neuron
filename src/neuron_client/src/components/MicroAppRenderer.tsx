import { useMemo, useState, useCallback, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { DynamicField } from "./DynamicField";
import { validateFieldValueWithZod, getDefaultFieldValue } from "../lib/microAppUtils";
import { MicroAppErrorBoundary } from "./MicroAppErrorBoundary";
import { useAppSelector } from "../hooks";
import { selectMicroApp, selectMicroAppRecord } from "../slices/microAppsSlice";

interface ViewConfig {
  fields: string[];
  actions?: string[];
  title?: string;
  description?: string;
}

interface ComponentConfig {
  type: string;
  label?: string;
  placeholder?: string;
  required?: boolean;
  readonly?: boolean;
  position?: number;
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

interface DisplaySchema {
  views: {
    list?: ViewConfig;
    detail?: ViewConfig;
    [key: string]: ViewConfig | undefined;
  };
  components: Record<string, ComponentConfig>;
}

interface MicroAppRendererProps {
  appId: string;
  recordId?: string;
  view?: string;
  readonly?: boolean;
  onFieldChange?: (fieldName: string, value: unknown) => void;
  onValidationErrors?: (errors: Record<string, string>) => void;
  optimisticUpdates?: boolean;
}

export function MicroAppRenderer({
  appId,
  recordId,
  view = "detail",
  readonly = false,
  onFieldChange,
  onValidationErrors,
  optimisticUpdates = false,
}: MicroAppRendererProps) {
  const app = useAppSelector(selectMicroApp(appId));
  const record = useAppSelector(recordId ? selectMicroAppRecord(appId, recordId) : () => undefined);

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formData, setFormData] = useState<Record<string, unknown>>({});

  // Notify parent of validation errors
  useEffect(() => {
    onValidationErrors?.(fieldErrors);
  }, [fieldErrors, onValidationErrors]);

  // Parse display schema with enhanced error handling
  const displaySchema = useMemo((): DisplaySchema => {
    if (!app || !app.display_schema) {
      return { views: {}, components: {} };
    }

    try {
      const schema = app.display_schema as unknown as DisplaySchema;

      // Validate schema structure
      if (typeof schema !== 'object' || schema === null) {
        console.warn('Display schema is not a valid object:', schema);
        return { views: {}, components: {} };
      }

      // Ensure required properties exist
      const validatedSchema: DisplaySchema = {
        views: schema.views && typeof schema.views === 'object' ? schema.views : {},
        components: schema.components && typeof schema.components === 'object' ? schema.components : {},
      };

      return validatedSchema;
    } catch (error) {
      console.error('Error parsing display schema:', error);
      return { views: {}, components: {} };
    }
  }, [app]);

  // Get current view configuration with error handling
  const viewConfig = useMemo((): ViewConfig => {
    try {
      const config = displaySchema.views[view];
      const baseConfig = config ? { ...config } : {
        fields: Object.keys(displaySchema.components),
        title: `${view.charAt(0).toUpperCase() + view.slice(1)} View`,
      };

      // Validate fields array
      if (!Array.isArray(baseConfig.fields)) {
        console.warn('View config fields is not an array, using component keys');
        baseConfig.fields = Object.keys(displaySchema.components);
      }

      // Add actions based on URL - only show save/cancel when not readonly
      if (!readonly) {
        baseConfig.actions = ["save", "cancel"];
      }

      return baseConfig;
    } catch (error) {
      console.error('Error processing view configuration:', error);
      return {
        fields: [],
        title: 'Error View',
      };
    }
  }, [displaySchema, view, readonly]);

  // Get field values
  const fieldValues = useMemo(() => {
    const values: Record<string, unknown> = {};

    // Use form data if not readonly, otherwise use record data
    const dataSource = !readonly ? { ...record?.data, ...formData } : record?.data;

    viewConfig.fields.forEach(fieldName => {
      const componentConfig = displaySchema.components[fieldName];
      values[fieldName] = dataSource?.[fieldName] ?? getDefaultFieldValue(componentConfig || { type: "input" });
    });

    return values;
  }, [viewConfig.fields, displaySchema.components, record?.data, formData, readonly]);

  // Handle field changes
  const handleFieldChange = useCallback((fieldName: string, value: unknown) => {
    try {
      // Update local form data
      setFormData(prev => ({ ...prev, [fieldName]: value }));

      // Real-time validation: validate immediately as user types
      const componentConfig = displaySchema.components[fieldName];
      if (componentConfig) {
        try {
          const error = validateFieldValueWithZod(value, componentConfig, fieldName);
          if (error) {
            setFieldErrors(prev => ({ ...prev, [fieldName]: error }));
          } else {
            // Clear field error if validation passes
            setFieldErrors(prev => {
              const newErrors = { ...prev };
              delete newErrors[fieldName];
              return newErrors;
            });
          }
        } catch (validationError) {
          console.error(`Validation error for field ${fieldName}:`, validationError);
          setFieldErrors(prev => ({ ...prev, [fieldName]: "Validation failed" }));
        }
      }

      // Call parent handler
      onFieldChange?.(fieldName, value);
    } catch (error) {
      console.error(`Error handling field change for ${fieldName}:`, error);
      // Set a generic error message instead of crashing
      setFieldErrors(prev => ({ ...prev, [fieldName]: "Invalid input" }));
    }
  }, [displaySchema.components, onFieldChange]);


  if (!app) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-muted-foreground">Micro-app not found</p>
        </CardContent>
      </Card>
    );
  }

  if (!app.display_schema) {
    return (
      <MicroAppErrorBoundary>
        <Card>
          <CardContent className="p-6">
            <p className="text-muted-foreground">No display configuration found</p>
          </CardContent>
        </Card>
      </MicroAppErrorBoundary>
    );
  }

  // Check if display schema is malformed
  if (Object.keys(displaySchema.components).length === 0 && viewConfig.fields.length === 0) {
    return (
      <MicroAppErrorBoundary>
        <Card>
          <CardContent className="p-6">
            <div className="p-2 border border-orange-300 bg-orange-50 rounded">
              <p className="text-sm text-orange-700">
                Display schema appears to be malformed or empty. No components or fields are defined.
              </p>
            </div>
          </CardContent>
        </Card>
      </MicroAppErrorBoundary>
    );
  }

  return (
    <MicroAppErrorBoundary>
      <Card>
        <CardContent className="p-6 space-y-4">
          {viewConfig.fields
            .map(fieldName => ({
              fieldName,
              componentConfig: displaySchema.components[fieldName],
              position: displaySchema.components[fieldName]?.position ?? Number.MAX_SAFE_INTEGER
            }))
            .sort((a, b) => a.position - b.position)
            .map(({ fieldName, componentConfig }) => {

            if (!componentConfig) {
              console.warn(`No component config found for field: ${fieldName}`);
              return (
                <div key={fieldName} className="p-2 border border-orange-300 bg-orange-50 rounded">
                  <p className="text-sm text-orange-700">
                    Field configuration missing: {fieldName}
                  </p>
                </div>
              );
            }

            const fieldConfig = {
              ...componentConfig,
              readonly: readonly || componentConfig.readonly,
            };


            return (
              <DynamicField
                key={fieldName}
                name={fieldName}
                config={fieldConfig}
                value={fieldValues[fieldName]}
                onChange={(value) => handleFieldChange(fieldName, value)}
                error={fieldErrors[fieldName]}
                appId={appId}
                recordId={recordId}
                optimisticUpdates={optimisticUpdates}
              />
            );
          })}

          {viewConfig.fields.length === 0 && (
            <p className="text-center text-muted-foreground py-8">
              No fields configured for this view
            </p>
          )}
        </CardContent>
      </Card>
    </MicroAppErrorBoundary>
  );
}

import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Save, X, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { MicroAppRenderer } from "./MicroAppRenderer";
import { MicroAppErrorBoundary } from "./MicroAppErrorBoundary";
import { useAppDispatch, useAppSelector } from "../hooks";
import {
  selectMicroApp,
  selectMicroAppRecord,
  createMicroAppData,
  updateMicroAppData,
  fetchMicroAppData,
} from "../slices/microAppsSlice";
import { sanitizeFormData, validateFormDataWithZod } from "../lib/microAppUtils";

interface MicroAppDetailViewProps {
  appId: string;
  recordId?: string; // undefined for new records
  mode: "view" | "edit" | "create";
  readonly?: boolean;
  onSave?: (recordId: string) => void;
  onCancel?: () => void;
  showActions?: boolean;
}

export function MicroAppDetailView({
  appId,
  recordId,
  mode,
  readonly = false,
  onSave,
  onCancel,
  showActions = true,
}: MicroAppDetailViewProps) {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const app = useAppSelector(selectMicroApp(appId));
  const record = useAppSelector(recordId ? selectMicroAppRecord(appId, recordId) : () => undefined);

  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingRecord, setLoadingRecord] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Fetch record data when recordId changes (but not for create mode)
  useEffect(() => {
    if (recordId && mode !== "create" && !record && app) {
      setLoadingRecord(true);
      dispatch(fetchMicroAppData({ appId }))
        .then((action) => {
          setLoadingRecord(false);
          if (fetchMicroAppData.rejected.match(action)) {
            console.error("Failed to fetch micro app data:", action.error);
            setError("Failed to load record data");
          }
        })
        .catch((err) => {
          console.error("Failed to fetch micro app data:", err);
          setLoadingRecord(false);
          setError("Failed to load record data");
        });
    }
  }, [dispatch, appId, recordId, mode, record, app]);

  // Initialize form data when record loads
  useEffect(() => {
    if (record && mode !== "create") {
      setFormData(record.data);
    }
  }, [record, mode]);

  // Handle field changes
  const handleFieldChange = useCallback((fieldName: string, value: unknown) => {
    setFormData(prev => ({ ...prev, [fieldName]: value }));
    setError(null); // Clear error on change
  }, []);

  // Handle validation errors from renderer
  const handleValidationErrors = useCallback((errors: Record<string, string>) => {
    setValidationErrors(errors);
  }, []);

  // Handle save action
  const handleSave = async () => {
    if (!app) return;


    setSaving(true);
    setError(null);

    try {
      // Get component configs for validation and sanitization
      const displaySchema = app.display_schema as Record<string, unknown>;
      const componentConfigs = (displaySchema?.components || {}) as Record<string, unknown>;

      // First, validate with Zod as a safety net
      const validationResult = validateFormDataWithZod(formData, componentConfigs);
      if (!validationResult.success) {
        // If validation fails, show errors and stop
        setValidationErrors(validationResult.errors);
        const firstError = Object.values(validationResult.errors)[0];
        throw new Error(`Validation failed: ${firstError}`);
      }

      // Clear any previous validation errors
      setValidationErrors({});

      // Use the validated data from Zod (which includes proper type coercion)
      const validatedData = validationResult.data;

      // Sanitize the validated data before sending to API
      const sanitizedData = sanitizeFormData(validatedData, componentConfigs);
      console.log("Saving data:", { mode, appId, recordId });

      let result;

      if (mode === "create") {
        const action = await dispatch(createMicroAppData({
          appId,
          data: sanitizedData,
        }));

        if (createMicroAppData.fulfilled.match(action)) {
          result = action.payload;
          toast.success("Record created successfully");
          onSave?.(result.record.id);
          // Navigate to the new record in view mode
          navigate(`/micro-apps/${appId}/record/${result.record.id}`);
        } else {
          // Handle the rejected case
          throw new Error(action.error?.message || "Failed to create record");
        }
      } else {
        if (!recordId) throw new Error("Record ID required for update");

        const action = await dispatch(updateMicroAppData({
          appId,
          recordId,
          data: sanitizedData,
          partial: true,
        }));

        if (updateMicroAppData.fulfilled.match(action)) {
          result = action.payload;
          toast.success("Record updated successfully");
          onSave?.(recordId);
          // Navigate to the updated record in view mode
          navigate(`/micro-apps/${appId}/record/${recordId}`);
        } else {
          // Handle the rejected case
          throw new Error(action.error?.message || "Failed to update record");
        }
      }


    } catch (err: unknown) {
      console.error("Save error:", err);

      let errorMessage = "Failed to save record";

      // Parse API error response for field-specific errors
      if (err && typeof err === "object" && "message" in err) {
        const error = err as { message?: string; response?: { data?: unknown } };

        // Check for validation errors in the response
        if (error.message && typeof error.message === "string") {
          // Try to parse structured error messages
          if (error.message.includes("validation")) {
            errorMessage = "Please check your input values and try again.";
          } else {
            errorMessage = error.message;
          }
        }

        // If there's additional error detail, log it
        if (error.response?.data) {
          console.error("API error details:", error.response.data);
        }
      }

      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setSaving(false);
    }
  };


  // Handle cancel action
  const handleCancel = () => {
    if (mode === "create") {
      onCancel?.();
      navigate(`/micro-apps/${appId}`);
    } else {
      // Navigate back to view mode
      navigate(`/micro-apps/${appId}/record/${recordId}`);
      onCancel?.();
    }
  };


  if (!app) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center space-x-2">
            <Skeleton className="h-4 w-4" />
            <Skeleton className="h-4 w-[200px]" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Show loading state while fetching record data
  if (loadingRecord) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <Skeleton className="h-8 w-8" />
              <Skeleton className="h-6 w-48" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-10 w-full" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-10 w-full" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Show error if record should exist but wasn't found
  if (recordId && mode !== "create" && !record && !loadingRecord) {
    return (
      <Card>
        <CardContent className="p-6">
          <Alert variant="destructive">
            <AlertDescription>
              Record not found. It may have been deleted or you may not have access to it.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  const isEditing = mode === "edit" || mode === "create";

  return (
    <MicroAppErrorBoundary>
      <div className="space-y-4">
        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Main Content */}
        <MicroAppErrorBoundary
          fallback={
            <Card>
              <CardContent className="p-6">
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    Unable to render the form. This may be due to an invalid display schema configuration.
                    Please check that the micro-app has a properly structured display schema.
                  </AlertDescription>
                </Alert>
              </CardContent>
            </Card>
          }
        >
          <MicroAppRenderer
            appId={appId}
            recordId={recordId}
            view="detail"
            readonly={readonly}
            onFieldChange={handleFieldChange}
            onValidationErrors={handleValidationErrors}
            optimisticUpdates={false} // Disable for form mode
          />
        </MicroAppErrorBoundary>

        {/* Footer Actions */}
        {showActions && isEditing && (
          <Card>
            <CardFooter className="flex justify-between p-4">
              <Button
                variant="outline"
                onClick={handleCancel}
                disabled={saving}
              >
                <X className="h-4 w-4 mr-2" />
                Cancel
              </Button>

              <Button
                onClick={handleSave}
                disabled={saving || Object.keys(validationErrors).length > 0}
              >
                <Save className="h-4 w-4 mr-2" />
                {saving ? "Saving..." : "Save"}
              </Button>
            </CardFooter>
          </Card>
        )}
      </div>
    </MicroAppErrorBoundary>
  );
}

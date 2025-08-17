import { useEffect } from "react";
import { Outlet, useParams, useNavigate, Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { AlertTriangle, ArrowLeft } from "lucide-react";
import { MicroAppErrorBoundary } from "./MicroAppErrorBoundary";
import { RoleGuard } from "./BetaFeatureGuard";
import { ROLES } from "../lib/auth";
import { useAppDispatch, useAppSelector } from "../hooks";
import {
  selectMicroApps,
  selectMicroApp,
  selectMicroAppsLoading,
  selectMicroAppsError,
  fetchMicroApps,
} from "../slices/microAppsSlice";

export function MicroAppContainer() {
  return (
    <RoleGuard role={ROLES.ADMIN}>
      <MicroAppContainerContent />
    </RoleGuard>
  );
}

function MicroAppContainerContent() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { appId, recordId } = useParams<{ appId: string; recordId?: string }>();

  const apps = useAppSelector(selectMicroApps);
  const app = useAppSelector(appId ? selectMicroApp(appId) : () => undefined);
  const loading = useAppSelector(selectMicroAppsLoading);
  const error = useAppSelector(selectMicroAppsError);

  // Load apps on mount if not loaded
  useEffect(() => {
    if (apps.length === 0 && !loading) {
      dispatch(fetchMicroApps());
    }
  }, [dispatch, apps.length, loading]);


  // Show loading state while fetching apps
  if (loading && apps.length === 0) {
    return (
      <div className="flex flex-1 p-4 ipad-top-spacing flex-col flex-nowrap max-h-screen">
        <div className="flex items-center justify-between mb-2 border-b pb-2 mobile-safe-top">
          <SidebarTrigger className="size-10 mr-2" />
          <h1 className="text-lg lg:text-2xl font-bold">
            <Skeleton className="h-6 w-48" />
          </h1>
          <div className="flex-1" />
        </div>
        <div className="space-y-4">
          <Card>
            <CardContent className="p-6">
              <div className="space-y-4">
                <Skeleton className="h-8 w-64" />
                <div className="space-y-2">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="flex flex-1 p-4 ipad-top-spacing flex-col flex-nowrap max-h-screen">
        <div className="flex items-center justify-between mb-2 border-b pb-2 mobile-safe-top">
          <SidebarTrigger className="size-10 mr-2" />
          <h1 className="text-lg lg:text-2xl font-bold">Micro Apps</h1>
          <div className="flex-1" />
        </div>
        <div className="space-y-4">
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Failed to load micro apps: {error}
            </AlertDescription>
          </Alert>
        </div>
      </div>
    );
  }

  // Show app not found error for specific app routes
  if (appId && !app && apps.length > 0) {
    return (
      <div className="flex flex-1 p-4 ipad-top-spacing flex-col flex-nowrap max-h-screen">
        <div className="flex items-center justify-between mb-2 border-b pb-2 mobile-safe-top">
          <SidebarTrigger className="size-10 mr-2" />
          <h1 className="text-lg lg:text-2xl font-bold">Micro Apps</h1>
          <div className="flex-1" />
        </div>
        <div className="space-y-4">
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Micro app not found. It may have been deleted or you may not have access to it.
            </AlertDescription>
          </Alert>
        </div>
      </div>
    );
  }

  return (
    <MicroAppErrorBoundary>
      <div className="flex flex-1 p-4 ipad-top-spacing flex-col flex-nowrap max-h-screen">
        {/* Header matching thread view */}
        <div className="flex items-center justify-between mb-2 border-b pb-2 mobile-safe-top">
          <SidebarTrigger className="size-10 mr-2" />
          <h1 className="text-lg lg:text-2xl font-bold">
            {app && (
              <Button
                className="mr-4"
                variant="ghost"
                size="icon"
                onClick={() => {
                  // If we're on a record page, go back to the app list
                  // If we're on an app page, go back to the root micro-apps list
                  if (recordId) {
                    navigate(`/micro-apps/${appId}`);
                  } else {
                    navigate('/micro-apps');
                  }
                }}
              >
                <ArrowLeft className="size-4" />
              </Button>
            )}
            {app ? app.name : "Micro Apps"}
          </h1>
          <div className="flex-1" />
        </div>


        {/* Main Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="min-h-[600px]">
            <Outlet />
          </div>
        </div>
      </div>
    </MicroAppErrorBoundary>
  );
}

// Helper component for the main micro apps index page
export function MicroAppsIndex() {
  const apps = useAppSelector(selectMicroApps);
  const loading = useAppSelector(selectMicroAppsLoading);

  if (loading && apps.length === 0) {
    return (
      <div className="space-y-4 p-4">
        {[...Array(3)].map((_, i) => (
          <Card key={i}>
            <CardContent className="p-6">
              <div className="space-y-2">
                <Skeleton className="h-6 w-48" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (apps.length === 0) {
    return (
      <div className="p-4">
        <Card>
          <CardContent className="p-12 text-center">
            <h3 className="text-lg font-medium mb-2">No Micro Apps</h3>
            <p className="text-muted-foreground mb-4">
              No micro apps have been created yet.
            </p>
            <p className="text-sm text-muted-foreground">
              Micro apps are created by AI agents to store and manage structured data.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {apps.map((app) => (
          <Card key={app.id} className="hover:shadow-md transition-shadow">
            <CardContent className="p-6">
              <h3 className="font-semibold mb-2">
                <Link
                  to={`/micro-apps/${app.id}`}
                  className="hover:text-primary transition-colors"
                >
                  {app.name}
                </Link>
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                {app.description}
              </p>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Actions: {app.actions.length}</span>
                <span>Created: {new Date(app.created_at).toLocaleDateString()}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Plus, Search, MoreVertical, Eye, Edit, Trash2 } from "lucide-react";
import { MicroAppErrorBoundary } from "./MicroAppErrorBoundary";
import { useAppDispatch, useAppSelector } from "../hooks";
import {
  selectMicroApp,
  selectMicroAppData,
  selectMicroAppDataLoading,
  fetchMicroAppData,
  deleteMicroAppData,
} from "../slices/microAppsSlice";

interface MicroAppListViewProps {
  appId: string;
  onCreateNew?: () => void;
  onEdit?: (recordId: string) => void;
  onView?: (recordId: string) => void;
  onDelete?: (recordId: string) => void;
}

export function MicroAppListView({
  appId,
  onCreateNew,
  onEdit,
  onView,
  onDelete,
}: MicroAppListViewProps) {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const app = useAppSelector(selectMicroApp(appId));
  const records = useAppSelector(selectMicroAppData(appId));
  const loading = useAppSelector(selectMicroAppDataLoading(appId));

  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage] = useState(1);
  const itemsPerPage = 20;

  // Load data on mount
  useEffect(() => {
    dispatch(fetchMicroAppData({
      appId,
      limit: itemsPerPage,
      offset: (currentPage - 1) * itemsPerPage
    }));
  }, [dispatch, appId, currentPage]);

  // Get display configuration
  const { listFields, componentConfigs } = useMemo(() => {
    if (!app?.display_schema) {
      return { listFields: [], componentConfigs: {} };
    }

    const displaySchema = app.display_schema as Record<string, unknown>;
    const views = displaySchema.views as Record<string, { fields?: string[] }>;
    const listView = views?.list;
    const components = displaySchema.components as Record<string, unknown>;

    return {
      listFields: listView?.fields || Object.keys(components || {}),
      componentConfigs: components || {},
    };
  }, [app]);

  // Filter records based on search
  const filteredRecords = useMemo(() => {
    if (!searchQuery) return records;

    return records.filter(record =>
      Object.values(record.data).some((value: unknown) =>
        String(value).toLowerCase().includes(searchQuery.toLowerCase())
      )
    );
  }, [records, searchQuery]);

  // Handle row click for navigation
  const handleRowClick = (recordId: string) => {
    if (onView) {
      onView(recordId);
    } else {
      navigate(`/micro-apps/${appId}/record/${recordId}`);
    }
  };

  // Handle delete action
  const handleDelete = async (recordId: string) => {
    if (window.confirm("Are you sure you want to delete this record?")) {
      try {
        await dispatch(deleteMicroAppData({ appId, recordId }));
        onDelete?.(recordId);
      } catch (error) {
        console.error("Failed to delete record:", error);
      }
    }
  };

  // Format cell value based on component type
  const formatCellValue = (value: unknown, fieldName: string) => {
    const config = componentConfigs[fieldName] as { type?: string; options?: Array<{ value: string; label: string }> };

    if (value === null || value === undefined) {
      return <span className="text-muted-foreground">—</span>;
    }

    switch (config?.type) {
      case "checkbox":
        return (
          <Badge variant={value ? "default" : "secondary"}>
            {value ? "Yes" : "No"}
          </Badge>
        );

      case "date":
        return new Date(String(value)).toLocaleDateString();

      case "select": {
        const option = config.options?.find((opt: { value: string; label: string }) => opt.value === value);
        return option?.label || String(value);
      }

      case "email": {
        return (
          <a href={`mailto:${String(value)}`} className="text-blue-600 hover:underline">
            {String(value)}
          </a>
        );
      }

      default: {
        const stringValue = String(value);
        return stringValue.length > 50
          ? `${stringValue.substring(0, 50)}...`
          : stringValue;
      }
    }
  };

  if (!app) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-center text-muted-foreground">Micro-app not found</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <MicroAppErrorBoundary>
      <div className="p-4">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardDescription>{app.description}</CardDescription>
              </div>

              <div className="flex items-center gap-2">
                {listFields.length > 0 && (
                  <>
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        placeholder="Search records..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-9 w-64"
                      />
                    </div>

                    <Button
                      onClick={() => onCreateNew?.() || navigate(`/micro-apps/${appId}/record/new`)}
                      size="sm"
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      New Record
                    </Button>
                  </>
                )}
              </div>
            </div>
          </CardHeader>

          <CardContent>
            {listFields.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-muted-foreground">
                  No display configuration found.
                </p>
              </div>
            ) : loading ? (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : filteredRecords.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-muted-foreground mb-4">
                  {searchQuery ? "No records match your search." : "No records found."}
                </p>
                {!searchQuery && (
                  <Button
                    onClick={() => onCreateNew?.() || navigate(`/micro-apps/${appId}/record/new`)}
                    variant="outline"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Create First Record
                  </Button>
                )}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    {listFields.map((fieldName: string) => (
                      <TableHead key={fieldName} className="font-medium">
                        {(componentConfigs[fieldName] as { label?: string })?.label || fieldName}
                      </TableHead>
                    ))}
                    <TableHead className="w-12"></TableHead>
                  </TableRow>
                </TableHeader>

                <TableBody>
                  {filteredRecords.map((record) => (
                    <TableRow
                      key={record.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => handleRowClick(record.id)}
                    >
                      {listFields.map((fieldName: string) => (
                        <TableCell key={fieldName}>
                          {formatCellValue(record.data[fieldName], fieldName)}
                        </TableCell>
                      ))}

                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger
                            asChild
                            onClick={(e) => e.stopPropagation()}
                          >
                            <Button variant="ghost" size="sm">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>

                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRowClick(record.id);
                              }}
                            >
                              <Eye className="h-4 w-4 mr-2" />
                              View
                            </DropdownMenuItem>

                            <DropdownMenuItem
                              onClick={(e) => {
                                e.stopPropagation();
                                if (onEdit) {
                                  onEdit(record.id);
                                } else {
                                  navigate(`/micro-apps/${appId}/record/${record.id}/edit`);
                                }
                              }}
                            >
                              <Edit className="h-4 w-4 mr-2" />
                              Edit
                            </DropdownMenuItem>

                            <DropdownMenuItem
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDelete(record.id);
                              }}
                              className="text-destructive"
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </MicroAppErrorBoundary>
  );
}

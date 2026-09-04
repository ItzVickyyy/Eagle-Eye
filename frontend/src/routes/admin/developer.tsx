import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import {
  Activity,
  CheckCircle2,
  Cpu,
  Database,
  Layers,
  RefreshCw,
  Server,
  Shield,
  Sliders,
  Terminal,
} from "lucide-react"
import { useState } from "react"

import {
  DeveloperService,
  type FeatureFlagsUpdate,
  UsersService,
} from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/admin/developer")({
  component: DeveloperDashboard,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    if (!user.is_developer) {
      throw redirect({
        to: "/admin",
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Developer System Dashboard — Eagle Eye",
      },
    ],
  }),
})

function DeveloperDashboard() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [activeTab, setActiveTab] = useState("overview")

  const {
    data: health,
    isLoading: isHealthLoading,
    refetch: refetchHealth,
    isRefetching: isHealthRefetching,
  } = useQuery({
    queryKey: ["developerHealth"],
    queryFn: async () => (await DeveloperService.getSystemHealth()).data,
    refetchInterval: 30000,
  })

  const {
    data: diagnostics,
    isLoading: isDiagLoading,
    refetch: refetchDiag,
  } = useQuery({
    queryKey: ["developerDiagnostics"],
    queryFn: async () => (await DeveloperService.getSystemDiagnostics()).data,
  })

  const { data: featureFlags, isLoading: isFlagsLoading } = useQuery({
    queryKey: ["developerFeatureFlags"],
    queryFn: async () => (await DeveloperService.getFeatureFlags()).data,
  })

  const { data: logs, isLoading: isLogsLoading } = useQuery({
    queryKey: ["developerLogs"],
    queryFn: async () => (await DeveloperService.getSystemLogs()).data,
  })

  const updateFlagsMutation = useMutation({
    mutationFn: (flags: FeatureFlagsUpdate) =>
      DeveloperService.updateFeatureFlags({ body: flags }),
    onSuccess: () => {
      showSuccessToast("Feature flags updated successfully")
      queryClient.invalidateQueries({ queryKey: ["developerFeatureFlags"] })
    },
    onError: () => {
      showErrorToast("Failed to update feature flags")
    },
  })

  const handleRefreshAll = async () => {
    await Promise.all([
      refetchHealth(),
      refetchDiag(),
      queryClient.invalidateQueries({ queryKey: ["developerFeatureFlags"] }),
      queryClient.invalidateQueries({ queryKey: ["developerLogs"] }),
    ])
    showSuccessToast("System diagnostics refreshed")
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight">
              Developer System Dashboard
            </h1>
            <Badge
              variant="outline"
              className="border-purple-500 text-purple-600 dark:text-purple-400"
            >
              System Level
            </Badge>
          </div>
          <p className="text-muted-foreground mt-1">
            Technical maintenance, runtime diagnostics, and system-level
            configuration
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefreshAll}
            disabled={isHealthRefetching}
            className="gap-2"
          >
            <RefreshCw
              className={`size-4 ${isHealthRefetching ? "animate-spin" : ""}`}
            />
            Refresh Diagnostics
          </Button>
        </div>
      </div>

      {/* Primary Status Banner Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">System Status</CardTitle>
            <Activity className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isHealthLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="flex items-center gap-2">
                <CheckCircle2 className="size-5 text-green-500" />
                <span className="text-2xl font-bold capitalize">
                  {health?.status || "Healthy"}
                </span>
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              Environment:{" "}
              <span className="font-medium text-foreground">
                {health?.environment || "production"}
              </span>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">
              Database Latency
            </CardTitle>
            <Database className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isHealthLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="text-2xl font-bold">
                {health?.database_latency_ms ?? 0} ms
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              State:{" "}
              <span className="font-medium text-foreground capitalize">
                {health?.database_status || "connected"}
              </span>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">
              FastAPI Engine
            </CardTitle>
            <Server className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isHealthLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="text-2xl font-bold">
                v{health?.fastapi_version}
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-1">
              Python {health?.python_version}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">
              System Trust Boundary
            </CardTitle>
            <Shield className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
              Isolated
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Club RBAC strictly detached
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Tabs */}
      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="space-y-4"
      >
        <TabsList>
          <TabsTrigger value="overview" className="gap-2">
            <Cpu className="size-4" />
            System Runtime & Metrics
          </TabsTrigger>
          <TabsTrigger value="flags" className="gap-2">
            <Sliders className="size-4" />
            Feature Flags & Maintenance
          </TabsTrigger>
          <TabsTrigger value="logs" className="gap-2">
            <Terminal className="size-4" />
            Diagnostics Logs
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Database className="size-4 text-primary" />
                  Database Aggregations & Metrics
                </CardTitle>
                <CardDescription>
                  Live counts across domain entity tables in the active database
                </CardDescription>
              </CardHeader>
              <CardContent>
                {isDiagLoading ? (
                  <div className="space-y-2">
                    <Skeleton className="h-6 w-full" />
                    <Skeleton className="h-6 w-full" />
                    <Skeleton className="h-6 w-full" />
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Entity Table</TableHead>
                        <TableHead className="text-right">
                          Record Count
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      <TableRow>
                        <TableCell className="font-medium">
                          Articles (All Statuses)
                        </TableCell>
                        <TableCell className="text-right">
                          {diagnostics?.total_articles ?? 0}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">
                          Categories
                        </TableCell>
                        <TableCell className="text-right">
                          {diagnostics?.total_categories ?? 0}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">Tags</TableCell>
                        <TableCell className="text-right">
                          {diagnostics?.total_tags ?? 0}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">Comments</TableCell>
                        <TableCell className="text-right">
                          {diagnostics?.total_comments ?? 0}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">
                          Contact Inquiries
                        </TableCell>
                        <TableCell className="text-right">
                          {diagnostics?.total_contact_messages ?? 0}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">
                          Club Members
                        </TableCell>
                        <TableCell className="text-right">
                          {diagnostics?.total_members ?? 0}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">
                          Staff & User Accounts
                        </TableCell>
                        <TableCell className="text-right">
                          {diagnostics?.total_users ?? 0}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-medium">
                          Configured Site Settings
                        </TableCell>
                        <TableCell className="text-right">
                          {diagnostics?.system_settings_count ?? 0}
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Layers className="size-4 text-primary" />
                  Host Environment & Platform
                </CardTitle>
                <CardDescription>
                  Backend runtime and system specification details
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {isHealthLoading ? (
                  <div className="space-y-2">
                    <Skeleton className="h-6 w-full" />
                    <Skeleton className="h-6 w-full" />
                  </div>
                ) : (
                  <div className="divide-y rounded-lg border text-sm">
                    <div className="flex items-center justify-between p-3">
                      <span className="text-muted-foreground font-medium">
                        Database Dialect
                      </span>
                      <Badge variant="outline">
                        {diagnostics?.database_engine || "sqlite"}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between p-3">
                      <span className="text-muted-foreground font-medium">
                        Operating System
                      </span>
                      <span className="font-mono text-xs">
                        {health?.platform_system || "Windows/Linux"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-3">
                      <span className="text-muted-foreground font-medium">
                        Python Runtime
                      </span>
                      <span className="font-mono text-xs">
                        {health?.python_version}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-3">
                      <span className="text-muted-foreground font-medium">
                        FastAPI Version
                      </span>
                      <span className="font-mono text-xs">
                        {health?.fastapi_version}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-3">
                      <span className="text-muted-foreground font-medium">
                        Server UTC Timestamp
                      </span>
                      <span className="font-mono text-xs">
                        {health?.server_time_utc
                          ? new Date(health.server_time_utc).toISOString()
                          : "N/A"}
                      </span>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Feature Flags Tab */}
        <TabsContent value="flags" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Sliders className="size-4 text-primary" />
                Technical Feature Flags & Toggles
              </CardTitle>
              <CardDescription>
                Live operational flags controlled at the application level by
                technical maintainers
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {isFlagsLoading ? (
                <div className="space-y-4">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <div className="font-semibold text-sm">
                        Maintenance Mode
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Put the public site into temporary maintenance state for
                        upgrades
                      </div>
                    </div>
                    <Checkbox
                      checked={featureFlags?.maintenance_mode ?? false}
                      onCheckedChange={(checked) =>
                        updateFlagsMutation.mutate({
                          maintenance_mode: Boolean(checked),
                        })
                      }
                      disabled={updateFlagsMutation.isPending}
                    />
                  </div>

                  <div className="flex items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <div className="font-semibold text-sm">
                        Public Reader Comments
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Allow public visitors to post new comments on published
                        articles
                      </div>
                    </div>
                    <Checkbox
                      checked={featureFlags?.public_comments_enabled ?? true}
                      onCheckedChange={(checked) =>
                        updateFlagsMutation.mutate({
                          public_comments_enabled: Boolean(checked),
                        })
                      }
                      disabled={updateFlagsMutation.isPending}
                    />
                  </div>

                  <div className="flex items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <div className="font-semibold text-sm">
                        Contact Form Inquiries
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Accept new incoming message submissions through the
                        public Contact Us form
                      </div>
                    </div>
                    <Checkbox
                      checked={featureFlags?.contact_form_enabled ?? true}
                      onCheckedChange={(checked) =>
                        updateFlagsMutation.mutate({
                          contact_form_enabled: Boolean(checked),
                        })
                      }
                      disabled={updateFlagsMutation.isPending}
                    />
                  </div>

                  <div className="flex items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <div className="font-semibold text-sm">
                        Public Self-Registration
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Enable or disable the public user sign-up endpoint
                        (/signup)
                      </div>
                    </div>
                    <Checkbox
                      checked={featureFlags?.allow_public_signup ?? true}
                      onCheckedChange={(checked) =>
                        updateFlagsMutation.mutate({
                          allow_public_signup: Boolean(checked),
                        })
                      }
                      disabled={updateFlagsMutation.isPending}
                    />
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Logs Tab */}
        <TabsContent value="logs" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Terminal className="size-4 text-primary" />
                Structured Application Diagnostic Logs
              </CardTitle>
              <CardDescription>
                System startup, routing, and developer access events (sensitive
                credentials redacted)
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLogsLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[180px]">Timestamp</TableHead>
                      <TableHead className="w-[100px]">Level</TableHead>
                      <TableHead className="w-[160px]">Component</TableHead>
                      <TableHead>Event Message</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs?.data.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell className="font-mono text-xs text-muted-foreground">
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              log.level === "ERROR"
                                ? "destructive"
                                : log.level === "WARN"
                                  ? "secondary"
                                  : "outline"
                            }
                            className="text-xs font-mono"
                          >
                            {log.level}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-xs font-medium">
                          {log.component}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {log.message}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

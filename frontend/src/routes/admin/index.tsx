import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  ArrowRight,
  Clock,
  Eye,
  FileCheck,
  FileEdit,
  FileText,
  Globe,
  ListChecks,
  PlusCircle,
  Users,
} from "lucide-react"

import { AnalyticsService, ArticlesService } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import useAuth from "@/hooks/useAuth"
import { formatDate } from "@/utils"

export const Route = createFileRoute("/admin/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "Dashboard — Eagle Eye",
      },
    ],
  }),
})

function Dashboard() {
  const { user: currentUser } = useAuth()
  const isStaffAdmin =
    currentUser?.is_superuser ||
    currentUser?.role === "super_admin" ||
    currentUser?.role === "admin"

  const { data: analyticsRes } = useQuery({
    queryKey: ["dashboard-analytics"],
    queryFn: () => AnalyticsService.getAnalyticsOverview(),
    enabled: !!isStaffAdmin,
  })

  const { data: recentArticlesRes } = useQuery({
    queryKey: ["dashboard-recent-articles"],
    queryFn: () => ArticlesService.readArticles({ query: { limit: 5 } }),
  })

  const stats: any = (analyticsRes as any)?.data || analyticsRes
  const recentArticles: any[] =
    (recentArticlesRes?.data as any)?.data ||
    (recentArticlesRes as any)?.data ||
    []

  return (
    <div className="flex flex-col gap-8">
      {/* Welcome Bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Welcome back, {currentUser?.full_name || currentUser?.email}
          </h1>
          <p className="text-muted-foreground text-sm">
            Eagle Eye Newsroom & Editorial Workspace
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button asChild variant="outline" size="sm" className="gap-1.5">
            <Link to="/" target="_blank">
              <Globe className="size-4" />
              View Site
            </Link>
          </Button>
          <Button asChild size="sm" className="gap-1.5">
            <Link to="/admin/articles/new">
              <PlusCircle className="size-4" />
              New Article
            </Link>
          </Button>
        </div>
      </div>

      {/* Quick Metrics */}
      {isStaffAdmin && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Views
              </CardTitle>
              <Eye className="size-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {(stats?.total_views || 0).toLocaleString()}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Published
              </CardTitle>
              <FileCheck className="size-4 text-emerald-600 dark:text-emerald-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats?.published_articles || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Pending Review
              </CardTitle>
              <Clock className="size-4 text-amber-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats?.pending_articles || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Drafts
              </CardTitle>
              <FileEdit className="size-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats?.draft_articles || 0}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Quick Actions & Recent Activity */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold tracking-tight">
              Recent Articles
            </h2>
            <Button asChild variant="ghost" size="sm">
              <Link to="/admin/articles" className="gap-1 text-xs">
                View all <ArrowRight className="size-3.5" />
              </Link>
            </Button>
          </div>

          <div className="rounded-xl border bg-card divide-y overflow-hidden">
            {recentArticles.length === 0 ? (
              <div className="p-8 text-center text-sm text-muted-foreground">
                No articles found.
              </div>
            ) : (
              recentArticles.map((article) => (
                <div
                  key={article.id}
                  className="flex items-center justify-between p-4 hover:bg-muted/40 transition-colors"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="min-w-0">
                      <p className="font-semibold text-sm line-clamp-1">
                        {article.headline}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {article.category?.name || "General"} •{" "}
                        {formatDate(
                          article.date_published || article.created_at,
                        )}
                      </p>
                    </div>
                  </div>
                  <Badge
                    variant="outline"
                    className="capitalize text-xs shrink-0 ml-3"
                  >
                    {article.status}
                  </Badge>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Quick Links */}
        <div className="flex flex-col gap-4">
          <h2 className="text-lg font-bold tracking-tight">Quick Actions</h2>
          <div className="flex flex-col gap-2.5">
            <Button
              asChild
              variant="outline"
              className="justify-start gap-2.5 h-11"
            >
              <Link to="/admin/articles/new">
                <PlusCircle className="size-4 text-primary" />
                <span>Write a new story</span>
              </Link>
            </Button>
            <Button
              asChild
              variant="outline"
              className="justify-start gap-2.5 h-11"
            >
              <Link to="/admin/articles">
                <FileText className="size-4 text-muted-foreground" />
                <span>Manage all articles</span>
              </Link>
            </Button>
            {isStaffAdmin && (
              <>
                <Button
                  asChild
                  variant="outline"
                  className="justify-start gap-2.5 h-11"
                >
                  <Link to="/admin/review-queue">
                    <ListChecks className="size-4 text-amber-500" />
                    <span>Review pending stories</span>
                  </Link>
                </Button>
                <Button
                  asChild
                  variant="outline"
                  className="justify-start gap-2.5 h-11"
                >
                  <Link to="/admin/members">
                    <Users className="size-4 text-muted-foreground" />
                    <span>Manage club members</span>
                  </Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

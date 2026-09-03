import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  Clock,
  Eye,
  FileCheck,
  MessageSquare,
  TrendingUp,
} from "lucide-react"

import { AnalyticsService } from "@/client"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { formatDate } from "@/utils"

export const Route = createFileRoute("/admin/analytics")({
  component: Analytics,
  head: () => ({
    meta: [{ title: "Analytics — Eagle Eye" }],
  }),
})

function Analytics() {
  const { data: analyticsRes, isLoading } = useQuery({
    queryKey: ["admin-analytics-overview"],
    queryFn: () => AnalyticsService.getAnalyticsOverview(),
  })

  const stats: any = (analyticsRes as any)?.data || analyticsRes

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
        <p className="text-muted-foreground text-sm">
          Overview of publication activity, readership metrics, and top stories.
        </p>
      </div>

      {isLoading ? (
        <div className="rounded-xl border bg-card p-12 text-center text-muted-foreground">
          Loading analytics...
        </div>
      ) : (
        <>
          {/* Key Metric Cards */}
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
                <p className="text-xs text-muted-foreground mt-1">
                  Across all published stories
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Published Stories
                </CardTitle>
                <FileCheck className="size-4 text-emerald-600 dark:text-emerald-400" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {stats?.published_articles || 0}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Out of {stats?.total_articles || 0} total stories
                </p>
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
                <p className="text-xs text-muted-foreground mt-1">
                  Awaiting editorial approval
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Readers & Engagement
                </CardTitle>
                <MessageSquare className="size-4 text-blue-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {stats?.total_comments || 0}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Comments from readers
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Top Articles Table */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <TrendingUp className="size-5 text-primary" />
                <CardTitle className="text-lg">Most Read Stories</CardTitle>
              </div>
              <CardDescription>
                Stories ranked by total page views since publication.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-lg border overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">#</TableHead>
                      <TableHead>Headline</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead>Author</TableHead>
                      <TableHead>Published</TableHead>
                      <TableHead className="text-right">Views</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {!stats?.top_articles || stats.top_articles.length === 0 ? (
                      <TableRow>
                        <TableCell
                          colSpan={6}
                          className="h-24 text-center text-muted-foreground"
                        >
                          No view data recorded yet.
                        </TableCell>
                      </TableRow>
                    ) : (
                      stats.top_articles.map((article: any, index: number) => (
                        <TableRow key={article.id}>
                          <TableCell className="font-mono text-muted-foreground text-xs">
                            {index + 1}
                          </TableCell>
                          <TableCell>
                            <Link
                              to="/news/$slug"
                              params={{ slug: article.slug }}
                              target="_blank"
                              className="font-medium hover:underline line-clamp-1 text-sm"
                            >
                              {article.headline}
                            </Link>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-xs">
                              {article.category?.name || "General"}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {article.author?.full_name || article.author?.email}
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {formatDate(article.date_published || article.created_at)}
                          </TableCell>
                          <TableCell className="text-right font-mono font-semibold text-sm">
                            {article.views_count.toLocaleString()}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

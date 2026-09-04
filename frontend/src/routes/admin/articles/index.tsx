import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  Archive,
  CheckCircle,
  Eye,
  FileEdit,
  FileText,
  MoreVertical,
  PlusCircle,
  Search,
  Send,
  Trash2,
} from "lucide-react"
import { useState } from "react"

import { type ArticleStatus, ArticlesService } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { formatDate } from "@/utils"

export const Route = createFileRoute("/admin/articles/")({
  component: Articles,
  head: () => ({
    meta: [{ title: "Articles — Eagle Eye" }],
  }),
})

const statusBadgeVariants: Record<
  string,
  { label: string; className: string }
> = {
  draft: {
    label: "Draft",
    className: "bg-muted text-muted-foreground border-border",
  },
  pending: {
    label: "Pending Review",
    className:
      "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20",
  },
  published: {
    label: "Published",
    className:
      "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20",
  },
  archived: {
    label: "Archived",
    className:
      "bg-zinc-500/10 text-zinc-700 dark:text-zinc-400 border-zinc-500/20",
  },
}

function Articles() {
  const { user: currentUser } = useAuth()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const [activeTab, setActiveTab] = useState<string>("all")
  const [searchQuery, setSearchQuery] = useState<string>("")
  const [articleToDelete, setArticleToDelete] = useState<any | null>(null)

  const isStaffAdmin =
    currentUser?.is_superuser ||
    currentUser?.role === "super_admin" ||
    currentUser?.role === "admin"

  const { data: articlesRes, isLoading } = useQuery({
    queryKey: ["admin-articles", activeTab, searchQuery],
    queryFn: () =>
      ArticlesService.readArticles({
        query: {
          status:
            activeTab === "all" ? undefined : (activeTab as ArticleStatus),
          search: searchQuery.trim() || undefined,
          limit: 50,
        },
      }),
  })

  const articles: any[] =
    (articlesRes?.data as any)?.data || (articlesRes as any)?.data || []

  const deleteMutation = useMutation({
    mutationFn: (id: number) =>
      ArticlesService.deleteArticle({ path: { id: String(id) } }),
    onSuccess: () => {
      showSuccessToast("Article deleted successfully")
      setArticleToDelete(null)
      queryClient.invalidateQueries({ queryKey: ["admin-articles"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to delete article")
    },
  })

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: ArticleStatus }) =>
      ArticlesService.updateArticle({
        path: { id: String(id) },
        body: { status },
      }),
    onSuccess: (_, variables) => {
      showSuccessToast(`Article status updated to ${variables.status}`)
      queryClient.invalidateQueries({ queryKey: ["admin-articles"] })
      queryClient.invalidateQueries({ queryKey: ["review-queue"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to update article status")
    },
  })

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Articles</h1>
          <p className="text-muted-foreground text-sm">
            Manage your stories, drafts, and publication status.
          </p>
        </div>
        <Button asChild className="self-start sm:self-auto gap-2">
          <Link to="/admin/articles/new">
            <PlusCircle className="size-4" />
            New Article
          </Link>
        </Button>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="w-full sm:w-auto"
        >
          <TabsList className="grid grid-cols-5 w-full sm:w-auto">
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="draft">Drafts</TabsTrigger>
            <TabsTrigger value="pending">Pending</TabsTrigger>
            <TabsTrigger value="published">Published</TabsTrigger>
            <TabsTrigger value="archived">Archived</TabsTrigger>
          </TabsList>
        </Tabs>

        <div className="relative w-full sm:w-64">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search articles..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 h-9"
          />
        </div>
      </div>

      <div className="rounded-xl border bg-card overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[45%]">Article</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Author</TableHead>
              <TableHead>Date</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="h-32 text-center text-muted-foreground"
                >
                  Loading articles...
                </TableCell>
              </TableRow>
            ) : articles.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-40 text-center">
                  <div className="flex flex-col items-center justify-center gap-2">
                    <FileText className="size-8 text-muted-foreground/50" />
                    <p className="font-medium text-sm text-foreground">
                      No articles found
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {searchQuery
                        ? "Try searching with a different term"
                        : "Write your first story or draft to see it here"}
                    </p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              articles.map((article) => {
                const statusMeta =
                  statusBadgeVariants[article.status] ||
                  statusBadgeVariants.draft
                const authorName =
                  article.author?.full_name ||
                  article.author?.email ||
                  "Unknown"

                return (
                  <TableRow key={article.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        {article.cover_image_url ? (
                          <img
                            src={article.cover_image_url}
                            alt=""
                            className="size-10 rounded object-cover shrink-0 border"
                          />
                        ) : (
                          <div className="size-10 rounded bg-muted flex items-center justify-center shrink-0 border">
                            <FileText className="size-5 text-muted-foreground" />
                          </div>
                        )}
                        <div className="min-w-0">
                          <p className="font-semibold text-sm line-clamp-1">
                            {article.headline}
                          </p>
                          <p className="text-xs text-muted-foreground line-clamp-1">
                            {article.slug}
                          </p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs font-normal">
                        {article.category?.name || "Uncategorized"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={`text-xs capitalize font-medium ${statusMeta.className}`}
                      >
                        {statusMeta.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {authorName}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDate(article.date_published || article.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-8"
                          >
                            <MoreVertical className="size-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48">
                          {article.status === "published" && (
                            <DropdownMenuItem asChild>
                              <Link
                                to="/news/$slug"
                                params={{ slug: article.slug }}
                                target="_blank"
                                className="cursor-pointer"
                              >
                                <Eye className="mr-2 size-4" />
                                View Public
                              </Link>
                            </DropdownMenuItem>
                          )}

                          <DropdownMenuItem asChild>
                            <Link
                              to="/admin/articles/new"
                              search={{ editId: article.id } as any}
                              className="cursor-pointer"
                            >
                              <FileEdit className="mr-2 size-4" />
                              Edit Article
                            </Link>
                          </DropdownMenuItem>

                          {article.status === "draft" && (
                            <DropdownMenuItem
                              onClick={() =>
                                updateStatusMutation.mutate({
                                  id: article.id,
                                  status: "pending",
                                })
                              }
                            >
                              <Send className="mr-2 size-4 text-amber-500" />
                              Submit for Review
                            </DropdownMenuItem>
                          )}

                          {isStaffAdmin && article.status !== "published" && (
                            <DropdownMenuItem
                              onClick={() =>
                                updateStatusMutation.mutate({
                                  id: article.id,
                                  status: "published",
                                })
                              }
                            >
                              <CheckCircle className="mr-2 size-4 text-emerald-500" />
                              Publish Now
                            </DropdownMenuItem>
                          )}

                          {isStaffAdmin && article.status === "published" && (
                            <DropdownMenuItem
                              onClick={() =>
                                updateStatusMutation.mutate({
                                  id: article.id,
                                  status: "archived",
                                })
                              }
                            >
                              <Archive className="mr-2 size-4 text-zinc-500" />
                              Archive
                            </DropdownMenuItem>
                          )}

                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive cursor-pointer"
                            onClick={() => setArticleToDelete(article)}
                          >
                            <Trash2 className="mr-2 size-4" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </div>

      <Dialog
        open={!!articleToDelete}
        onOpenChange={(open) => !open && setArticleToDelete(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Article</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{articleToDelete?.headline}
              &rdquo;? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setArticleToDelete(null)}
              disabled={deleteMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() =>
                articleToDelete && deleteMutation.mutate(articleToDelete.id)
              }
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete Article"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

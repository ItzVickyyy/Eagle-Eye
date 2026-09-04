import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import {
  CalendarDays,
  CheckCircle,
  Eye,
  FileEdit,
  ListChecks,
  RotateCcw,
  User,
} from "lucide-react"
import { useState } from "react"

import { ArticlesService, UsersService } from "@/client"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { sanitizeHtml } from "@/lib/sanitize"
import { calculateReadTime, formatDate, getInitials } from "@/utils"

export const Route = createFileRoute("/admin/review-queue")({
  component: ReviewQueue,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    const isStaffAdmin =
      user.is_superuser ||
      user.role === "super_admin" ||
      user.role === "admin"
    if (!isStaffAdmin) {
      throw redirect({
        to: "/admin",
      })
    }
  },
  head: () => ({
    meta: [{ title: "Review Queue — Eagle Eye" }],
  }),
})

function ReviewQueue() {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [selectedArticle, setSelectedArticle] = useState<any | null>(null)

  const { data: queueRes, isLoading } = useQuery({
    queryKey: ["review-queue"],
    queryFn: () => ArticlesService.getReviewQueue(),
  })

  const articles: any[] =
    (queueRes?.data as any)?.data || (queueRes as any)?.data || []

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: "published" | "draft" }) =>
      ArticlesService.updateArticle({
        path: { id: String(id) },
        body: { status },
      }),
    onSuccess: (_, variables) => {
      const msg =
        variables.status === "published"
          ? "Article approved and published!"
          : "Article returned to draft."
      showSuccessToast(msg)
      setSelectedArticle(null)
      queryClient.invalidateQueries({ queryKey: ["review-queue"] })
      queryClient.invalidateQueries({ queryKey: ["admin-articles"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to update article status")
    },
  })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Review Queue</h1>
        <p className="text-muted-foreground text-sm">
          Review stories submitted by student contributors before publication.
        </p>
      </div>

      {isLoading ? (
        <div className="rounded-xl border bg-card p-12 text-center text-muted-foreground">
          Loading review queue...
        </div>
      ) : articles.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
          <div className="rounded-full bg-emerald-500/10 p-4 mb-4 text-emerald-600 dark:text-emerald-400">
            <CheckCircle className="size-8" />
          </div>
          <h3 className="text-lg font-semibold">Review queue is empty</h3>
          <p className="mt-1 text-muted-foreground text-sm max-w-xs">
            All submitted articles have been reviewed. New submissions will appear
            here automatically.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {articles.map((article) => {
            const authorName =
              article.author?.full_name || article.author?.email || "Contributor"

            return (
              <div
                key={article.id}
                className="rounded-xl border bg-card p-5 flex flex-col md:flex-row md:items-center justify-between gap-5 transition-shadow hover:shadow-sm"
              >
                <div className="flex items-start gap-4 flex-1">
                  {article.cover_image_url ? (
                    <img
                      src={article.cover_image_url}
                      alt=""
                      className="size-16 rounded-lg object-cover shrink-0 border"
                    />
                  ) : (
                    <div className="size-16 rounded-lg bg-muted flex items-center justify-center shrink-0 border">
                      <ListChecks className="size-6 text-muted-foreground" />
                    </div>
                  )}

                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        {article.category?.name || "General"}
                      </Badge>
                      <Badge className="bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20 text-xs">
                        Pending Review
                      </Badge>
                    </div>

                    <h3 className="font-semibold text-base line-clamp-1">
                      {article.headline}
                    </h3>

                    {article.excerpt && (
                      <p className="text-sm text-muted-foreground line-clamp-2">
                        {article.excerpt}
                      </p>
                    )}

                    <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground pt-1">
                      <span className="flex items-center gap-1.5">
                        <User className="size-3.5" /> {authorName}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <CalendarDays className="size-3.5" />
                        {formatDate(article.created_at)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 self-end md:self-center shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedArticle(article)}
                    className="gap-1.5"
                  >
                    <Eye className="size-4" />
                    Preview
                  </Button>

                  <Button asChild variant="outline" size="sm">
                    <Link
                      to="/admin/articles/new"
                      search={{ editId: article.id } as any}
                      className="gap-1.5"
                    >
                      <FileEdit className="size-4" />
                      Edit
                    </Link>
                  </Button>

                  <LoadingButton
                    variant="outline"
                    size="sm"
                    loading={updateStatusMutation.isPending}
                    onClick={() =>
                      updateStatusMutation.mutate({
                        id: article.id,
                        status: "draft",
                      })
                    }
                    className="gap-1.5 text-muted-foreground hover:text-foreground"
                  >
                    <RotateCcw className="size-3.5" />
                    Return
                  </LoadingButton>

                  <LoadingButton
                    variant="default"
                    size="sm"
                    loading={updateStatusMutation.isPending}
                    onClick={() =>
                      updateStatusMutation.mutate({
                        id: article.id,
                        status: "published",
                      })
                    }
                    className="gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white"
                  >
                    <CheckCircle className="size-4" />
                    Approve & Publish
                  </LoadingButton>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Full Article Preview Dialog */}
      <Dialog
        open={!!selectedArticle}
        onOpenChange={(open) => !open && setSelectedArticle(null)}
      >
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          {selectedArticle && (
            <div className="space-y-6">
              <DialogHeader>
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant="outline">
                    {selectedArticle.category?.name || "General"}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {formatDate(selectedArticle.created_at)} •{" "}
                    {calculateReadTime(selectedArticle.body)} min read
                  </span>
                </div>
                <DialogTitle className="font-serif text-2xl font-bold leading-tight">
                  {selectedArticle.headline}
                </DialogTitle>
                {selectedArticle.excerpt && (
                  <DialogDescription className="text-base text-muted-foreground">
                    {selectedArticle.excerpt}
                  </DialogDescription>
                )}
              </DialogHeader>

              {selectedArticle.cover_image_url && (
                <div className="aspect-video w-full overflow-hidden rounded-lg bg-muted">
                  <img
                    src={selectedArticle.cover_image_url}
                    alt=""
                    className="size-full object-cover"
                  />
                </div>
              )}

              <div
                className="prose-content space-y-4 text-sm leading-relaxed text-foreground border-y py-6"
                dangerouslySetInnerHTML={{
                  __html:
                    sanitizeHtml(selectedArticle.body) ||
                    "<p>No content provided.</p>",
                }}
              />

              <div className="flex items-center justify-between pt-2">
                <div className="flex items-center gap-2">
                  <Avatar className="size-8">
                    <AvatarFallback className="text-xs">
                      {getInitials(
                        selectedArticle.author?.full_name ||
                          selectedArticle.author?.email ||
                          "Author",
                      )}
                    </AvatarFallback>
                  </Avatar>
                  <div className="text-xs">
                    <p className="font-semibold">
                      {selectedArticle.author?.full_name ||
                        selectedArticle.author?.email}
                    </p>
                    <p className="text-muted-foreground">
                      {selectedArticle.author?.position_title || "Contributor"}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      updateStatusMutation.mutate({
                        id: selectedArticle.id,
                        status: "draft",
                      })
                    }
                  >
                    Return to Draft
                  </Button>
                  <Button
                    size="sm"
                    className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
                    onClick={() =>
                      updateStatusMutation.mutate({
                        id: selectedArticle.id,
                        status: "published",
                      })
                    }
                  >
                    <CheckCircle className="size-4" />
                    Approve & Publish
                  </Button>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

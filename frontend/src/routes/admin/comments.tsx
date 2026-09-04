import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  MessageSquare,
  Search,
  ShieldAlert,
  Trash2,
} from "lucide-react"
import { useState } from "react"

import { CommentsService, type CommentStatus } from "@/client"
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
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
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

export const Route = createFileRoute("/admin/comments")({
  component: CommentsModeration,
  head: () => ({
    meta: [{ title: "Comments Moderation — Eagle Eye" }],
  }),
})

const statusBadgeVariants: Record<
  string,
  { label: string; className: string }
> = {
  approved: {
    label: "Approved",
    className:
      "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20",
  },
  pending: {
    label: "Pending",
    className:
      "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20",
  },
  spam: {
    label: "Spam",
    className:
      "bg-destructive/10 text-destructive border-destructive/20",
  },
}

function CommentsModeration() {
  const { user: currentUser } = useAuth()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const [activeTab, setActiveTab] = useState<string>("all")
  const [searchQuery, setSearchQuery] = useState<string>("")
  const [commentToDelete, setCommentToDelete] = useState<any | null>(null)

  const isStaffAdmin =
    currentUser?.is_superuser ||
    currentUser?.role === "super_admin" ||
    currentUser?.role === "admin"

  const { data: commentsRes, isLoading } = useQuery({
    queryKey: ["admin-comments", activeTab],
    queryFn: () =>
      CommentsService.getAllComments({
        query: {
          status:
            activeTab === "all" ? undefined : (activeTab as CommentStatus),
          limit: 100,
        },
      }),
    enabled: !!isStaffAdmin,
  })

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: CommentStatus }) =>
      CommentsService.updateCommentStatus({
        path: { id },
        body: { status },
      }),
    onSuccess: (_, variables) => {
      showSuccessToast(
        `Comment marked as ${variables.status} successfully`
      )
      queryClient.invalidateQueries({ queryKey: ["admin-comments"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to update comment status")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) =>
      CommentsService.deleteComment({ path: { id } }),
    onSuccess: () => {
      showSuccessToast("Comment deleted successfully")
      setCommentToDelete(null)
      queryClient.invalidateQueries({ queryKey: ["admin-comments"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to delete comment")
    },
  })

  if (!isStaffAdmin) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center">
        <ShieldAlert className="size-12 text-destructive mb-3" />
        <h2 className="text-xl font-bold">Access Restricted</h2>
        <p className="text-muted-foreground text-sm mt-1 max-w-md">
          Comment moderation requires Editorial Staff or Administrator privileges.
        </p>
      </div>
    )
  }

  const rawComments: any[] =
    (commentsRes?.data as any)?.data || (commentsRes as any)?.data || []

  const filteredComments = rawComments.filter((c) => {
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase()
    return (
      c.guest_name?.toLowerCase().includes(q) ||
      c.guest_email?.toLowerCase().includes(q) ||
      c.body?.toLowerCase().includes(q) ||
      c.article_headline?.toLowerCase().includes(q)
    )
  })

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Comment Moderation</h1>
          <p className="text-muted-foreground text-sm">
            Review, approve, or remove reader comments across published stories.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="w-full sm:w-auto"
        >
          <TabsList>
            <TabsTrigger value="all">All Comments</TabsTrigger>
            <TabsTrigger value="pending">Pending</TabsTrigger>
            <TabsTrigger value="approved">Approved</TabsTrigger>
            <TabsTrigger value="spam">Spam</TabsTrigger>
          </TabsList>
        </Tabs>

        <div className="relative w-full sm:w-72">
          <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
          <Input
            placeholder="Search commenter, text, story..."
            className="pl-9 text-xs"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Comments Table */}
      <div className="rounded-md border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[180px]">Commenter</TableHead>
              <TableHead className="min-w-[240px]">Comment</TableHead>
              <TableHead className="w-[180px]">Story</TableHead>
              <TableHead className="w-[100px]">Status</TableHead>
              <TableHead className="w-[120px]">Submitted</TableHead>
              <TableHead className="w-[160px] text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center text-muted-foreground">
                  Loading comments...
                </TableCell>
              </TableRow>
            ) : filteredComments.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center text-muted-foreground">
                  <div className="flex flex-col items-center justify-center gap-1.5">
                    <MessageSquare className="size-6 text-muted-foreground/60" />
                    <span>No comments found</span>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              filteredComments.map((c) => {
                const badge =
                  statusBadgeVariants[c.status] || statusBadgeVariants.pending
                return (
                  <TableRow key={c.id}>
                    <TableCell className="align-top font-medium">
                      <div className="flex flex-col">
                        <span className="text-sm font-semibold text-foreground">
                          {c.guest_name}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {c.guest_email}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="align-top">
                      <p className="text-sm whitespace-pre-wrap text-foreground/90 max-h-32 overflow-y-auto">
                        {c.body}
                      </p>
                    </TableCell>
                    <TableCell className="align-top text-xs">
                      {c.article_headline ? (
                        <div className="flex flex-col gap-1">
                          <span className="line-clamp-2 font-medium">
                            {c.article_headline}
                          </span>
                          {c.article_slug && (
                            <Link
                              to="/news/$slug"
                              params={{ slug: c.article_slug }}
                              target="_blank"
                              className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline"
                            >
                              View story <ExternalLink className="size-3" />
                            </Link>
                          )}
                        </div>
                      ) : (
                        <span className="text-muted-foreground italic">
                          Article #{c.article_id.slice(0, 8)}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="align-top">
                      <Badge variant="outline" className={badge.className}>
                        {badge.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="align-top text-xs text-muted-foreground whitespace-nowrap">
                      {formatDate(c.created_at)}
                    </TableCell>
                    <TableCell className="align-top text-right">
                      <div className="flex items-center justify-end gap-1">
                        {c.status !== "approved" && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-8 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-500/10"
                            title="Approve Comment"
                            disabled={updateStatusMutation.isPending}
                            onClick={() =>
                              updateStatusMutation.mutate({
                                id: c.id,
                                status: "approved" as CommentStatus,
                              })
                            }
                          >
                            <CheckCircle2 className="size-4" />
                          </Button>
                        )}
                        {c.status !== "spam" && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-8 text-amber-600 hover:text-amber-700 hover:bg-amber-500/10"
                            title="Mark as Spam"
                            disabled={updateStatusMutation.isPending}
                            onClick={() =>
                              updateStatusMutation.mutate({
                                id: c.id,
                                status: "spam" as CommentStatus,
                              })
                            }
                          >
                            <AlertTriangle className="size-4" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                          title="Delete Comment"
                          onClick={() => setCommentToDelete(c)}
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={!!commentToDelete}
        onOpenChange={(open) => {
          if (!open) setCommentToDelete(null)
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete Comment</DialogTitle>
            <DialogDescription>
              Are you sure you want to permanently delete this comment by{" "}
              <strong>{commentToDelete?.guest_name}</strong>? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>

          {commentToDelete && (
            <div className="rounded-md border bg-muted/40 p-3 text-xs text-foreground/80 italic">
              "{commentToDelete.body}"
            </div>
          )}

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCommentToDelete(null)}
            >
              Cancel
            </Button>
            <LoadingButton
              variant="destructive"
              size="sm"
              loading={deleteMutation.isPending}
              onClick={() => {
                if (commentToDelete?.id) {
                  deleteMutation.mutate(commentToDelete.id)
                }
              }}
            >
              Delete
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

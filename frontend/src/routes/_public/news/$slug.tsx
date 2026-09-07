import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link, notFound } from "@tanstack/react-router"
import {
  CalendarDays,
  Clock,
  Eye,
  Link2,
  MessageSquare,
  Send,
} from "lucide-react"
import { useState } from "react"
import { FaFacebookF, FaXTwitter } from "react-icons/fa6"

import { ArticlesService, CommentsService } from "@/client"
import { ArticleCard } from "@/components/Public/ArticleCard"
import { SectionHeading } from "@/components/Public/SectionHeading"
import { LoadingState } from "@/components/Public/States"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import useCustomToast from "@/hooks/useCustomToast"
import { sanitizeHtml } from "@/lib/sanitize"
import { calculateReadTime, formatDate, getInitials } from "@/utils"

export const Route = createFileRoute("/_public/news/$slug")({
  component: ArticleDetail,
  head: () => ({
    meta: [{ title: "Article - Eagle Eye" }],
  }),
  notFoundComponent: () => <ArticleNotFound />,
})

function ArticleDetail() {
  const { slug } = Route.useParams()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const [commentName, setCommentName] = useState("")
  const [commentEmail, setCommentEmail] = useState("")
  const [commentBody, setCommentBody] = useState("")

  const {
    data: articleRes,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["article-detail", slug],
    queryFn: async () => {
      try {
        return await ArticlesService.getArticleBySlug({ path: { slug } })
      } catch (err: any) {
        if (err?.status === 404) {
          throw notFound()
        }
        throw err
      }
    },
  })

  const article: any = (articleRes as any)?.data || articleRes

  const { data: relatedRes } = useQuery({
    queryKey: ["related-articles", article?.category_id],
    queryFn: () =>
      ArticlesService.readArticles({
        query: {
          category_id: article?.category_id ?? undefined,
          limit: 3,
        },
      }),
    enabled: !!article,
  })

  const { data: commentsRes } = useQuery({
    queryKey: ["article-comments", article?.id],
    queryFn: () =>
      CommentsService.getArticleComments({
        path: { article_id: article!.id },
      }),
    enabled: !!article?.id,
  })

  const commentMutation = useMutation({
    mutationFn: async () => {
      if (!article?.id) return
      return await CommentsService.createComment({
        body: {
          article_id: article.id,
          guest_name: commentName.trim(),
          guest_email: commentEmail.trim(),
          body: commentBody.trim(),
        },
      })
    },
    onSuccess: () => {
      showSuccessToast("Comment submitted! It will be visible after moderation.")
      setCommentName("")
      setCommentEmail("")
      setCommentBody("")
      queryClient.invalidateQueries({
        queryKey: ["article-comments", article?.id],
      })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to post comment.")
    },
  })

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6 lg:px-8">
        <LoadingState />
      </div>
    )
  }

  if (error || !article) {
    return <ArticleNotFound />
  }

  const category = article.category
  const authorName = article.author?.full_name || "Eagle Eye Staff"
  const authorRole =
    article.author?.position_title ||
    article.author?.department ||
    "Staff Writer"
  const initials = getInitials(authorName)
  const readTime = calculateReadTime(article.body || article.excerpt)
  const relatedArticles: any[] =
    (relatedRes as any)?.data?.data || (relatedRes as any)?.data || []
  const related = relatedArticles.filter((a: any) => a.id !== article.id)
  const comments: any[] =
    (commentsRes as any)?.data?.data || (commentsRes as any)?.data || []

  const handleCommentSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!commentName || !commentEmail || !commentBody) {
      showErrorToast("Please fill in all comment fields.")
      return
    }
    commentMutation.mutate()
  }

  return (
    <article>
      <div className="mx-auto max-w-3xl px-4 pt-8 sm:px-6 lg:px-8">
        <nav className="mb-4 text-sm text-muted-foreground">
          <Link to="/" className="hover:text-foreground">
            Home
          </Link>
          <span className="mx-1.5" aria-hidden>
            /
          </span>
          <Link to="/news" className="hover:text-foreground">
            News
          </Link>
          {category && (
            <>
              <span className="mx-1.5" aria-hidden>
                /
              </span>
              <Link
                to="/news"
                search={{ category: category.slug }}
                className="hover:text-foreground"
              >
                {category.name}
              </Link>
            </>
          )}
        </nav>

        {category && (
          <Badge className="bg-primary text-primary-foreground">
            {category.name}
          </Badge>
        )}
        <h1 className="mt-3 text-balance font-serif text-3xl font-bold leading-tight tracking-tight text-foreground sm:text-4xl md:text-[2.75rem]">
          {article.headline}
        </h1>
        {article.excerpt && (
          <p className="mt-4 text-lg text-muted-foreground">
            {article.excerpt}
          </p>
        )}

        <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-y py-4">
          <div className="flex items-center gap-3">
            <Avatar className="size-10">
              <AvatarFallback>{initials}</AvatarFallback>
            </Avatar>
            <div className="text-sm">
              <p className="font-semibold text-foreground">{authorName}</p>
              <p className="text-muted-foreground">{authorRole}</p>
            </div>
          </div>
          <div className="flex flex-col items-end gap-1 text-sm text-muted-foreground sm:flex-row sm:items-center sm:gap-4">
            <span className="flex items-center gap-1.5">
              <CalendarDays className="size-4" />
              {formatDate(article.date_published || article.created_at)}
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="size-4" />
              {readTime} min read
            </span>
            <span className="flex items-center gap-1.5">
              <Eye className="size-4" />
              {article.views_count} views
            </span>
          </div>
        </div>
      </div>

      {article.cover_image_url && (
        <div className="mx-auto mt-6 max-w-5xl px-4 sm:px-6 lg:px-8">
          <div className="aspect-[16/9] w-full overflow-hidden rounded-xl bg-muted">
            <img
              src={article.cover_image_url}
              alt={article.headline}
              className="h-full w-full object-cover"
            />
          </div>
        </div>
      )}

      <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
        <div
          className="prose-content space-y-5 text-base leading-relaxed text-foreground/90 sm:text-lg"
          dangerouslySetInnerHTML={{
            __html: sanitizeHtml(article.body) || "<p>No content.</p>",
          }}
        />

        {article.tags && article.tags.length > 0 && (
          <div className="mt-8 flex flex-wrap gap-2">
            {article.tags.map((tag: any) => (
              <Badge key={tag.id} variant="secondary">
                #{tag.name}
              </Badge>
            ))}
          </div>
        )}

        {/* Social Share Buttons */}
        <div className="mt-8 flex items-center gap-3 border-t pt-6">
          <span className="text-sm font-medium text-muted-foreground">
            Share this story
          </span>
          <ShareButton
            label="Share on Facebook"
            href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(
              typeof window !== "undefined" ? window.location.href : "",
            )}`}
          >
            <FaFacebookF className="size-4" />
          </ShareButton>
          <ShareButton
            label="Share on Twitter"
            href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(
              article.headline,
            )}`}
          >
            <FaXTwitter className="size-4" />
          </ShareButton>
          <ShareButton
            label="Copy link"
            onClick={() => {
              if (typeof navigator !== "undefined" && navigator.clipboard) {
                navigator.clipboard.writeText(window.location.href)
                showSuccessToast("Link copied to clipboard!")
              }
            }}
          >
            <Link2 className="size-4" />
          </ShareButton>
        </div>

        {/* Comments Section */}
        <div className="mt-12 border-t pt-8">
          <div className="flex items-center gap-2 mb-6">
            <MessageSquare className="size-5 text-primary" />
            <h2 className="font-serif text-2xl font-bold">
              Comments ({comments.length})
            </h2>
          </div>

          {/* Comment submission form */}
          <form
            onSubmit={handleCommentSubmit}
            className="rounded-xl border p-5 bg-card space-y-4 mb-8"
          >
            <h3 className="font-semibold text-sm">Leave a comment</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                placeholder="Your Name"
                value={commentName}
                onChange={(e) => setCommentName(e.target.value)}
                required
              />
              <Input
                type="email"
                placeholder="Your Email"
                value={commentEmail}
                onChange={(e) => setCommentEmail(e.target.value)}
                required
              />
            </div>
            <Textarea
              placeholder="Join the discussion..."
              rows={3}
              value={commentBody}
              onChange={(e) => setCommentBody(e.target.value)}
              required
            />
            <Button
              type="submit"
              size="sm"
              disabled={commentMutation.isPending}
              className="gap-2"
            >
              <Send className="size-3.5" />
              {commentMutation.isPending ? "Posting..." : "Post Comment"}
            </Button>
          </form>

          {/* Comments List */}
          <div className="space-y-4">
            {comments.length === 0 ? (
              <p className="text-sm text-muted-foreground italic">
                No comments yet. Be the first to share your thoughts!
              </p>
            ) : (
              comments.map((c: any) => (
                <div
                  key={c.id}
                  className="rounded-lg border p-4 bg-muted/20 space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <p className="font-semibold text-sm">{c.guest_name}</p>
                    <span className="text-xs text-muted-foreground">
                      {formatDate(c.created_at)}
                    </span>
                  </div>
                  <p className="text-sm text-foreground/90">{c.body}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {related.length > 0 && (
        <div className="border-t bg-muted/30">
          <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
            <SectionHeading eyebrow={category?.name} title="Related Stories" />
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {related.map((a: any) => (
                <ArticleCard key={a.id} article={a} />
              ))}
            </div>
          </div>
        </div>
      )}
    </article>
  )
}

function ShareButton({
  label,
  href,
  onClick,
  children,
}: {
  label: string
  href?: string
  onClick?: () => void
  children: React.ReactNode
}) {
  const className =
    "flex size-9 items-center justify-center rounded-full border text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"

  if (href) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={label}
        className={className}
      >
        {children}
      </a>
    )
  }

  return (
    <button
      type="button"
      aria-label={label}
      className={className}
      onClick={onClick}
    >
      {children}
    </button>
  )
}

function ArticleNotFound() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center px-4 py-24 text-center sm:px-6 lg:px-8">
      <p className="font-serif text-6xl font-bold text-primary">404</p>
      <h1 className="mt-4 text-2xl font-bold text-foreground">
        Story not found
      </h1>
      <p className="mt-2 text-muted-foreground">
        The article you're looking for may have been moved or doesn't exist.
      </p>
      <Link
        to="/news"
        className="mt-6 inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90"
      >
        Browse all news
      </Link>
    </div>
  )
}

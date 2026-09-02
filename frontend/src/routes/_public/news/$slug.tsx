import { createFileRoute, Link, notFound } from "@tanstack/react-router"
import { CalendarDays, Clock, Link2 } from "lucide-react"
import { FaFacebookF, FaXTwitter } from "react-icons/fa6"

import { ArticleCard } from "@/components/Public/ArticleCard"
import { SectionHeading } from "@/components/Public/SectionHeading"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import {
  formatDate,
  getArticleBySlug,
  getCategoryBySlug,
  getRelatedArticles,
} from "@/data/mockNews"

export const Route = createFileRoute("/_public/news/$slug")({
  component: ArticleDetail,
  loader: ({ params }) => {
    const article = getArticleBySlug(params.slug)
    if (!article) {
      throw notFound()
    }
    return article
  },
  head: ({ loaderData }) => ({
    meta: loaderData
      ? [
          { title: `${loaderData.title} - Eagle Eye` },
          { name: "description", content: loaderData.excerpt },
        ]
      : [],
  }),
  notFoundComponent: () => <ArticleNotFound />,
})

function ArticleDetail() {
  const article = Route.useLoaderData()
  const category = getCategoryBySlug(article.category)
  const related = getRelatedArticles(article, 3)
  const initials = article.author.name
    .split(" ")
    .map((n) => n[0])
    .join("")

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
          {article.title}
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">{article.excerpt}</p>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-y py-4">
          <div className="flex items-center gap-3">
            <Avatar className="size-10">
              <AvatarFallback>{initials}</AvatarFallback>
            </Avatar>
            <div className="text-sm">
              <p className="font-semibold text-foreground">
                {article.author.name}
              </p>
              <p className="text-muted-foreground">{article.author.role}</p>
            </div>
          </div>
          <div className="flex flex-col items-end gap-1 text-sm text-muted-foreground sm:flex-row sm:items-center sm:gap-4">
            <span className="flex items-center gap-1.5">
              <CalendarDays className="size-4" />
              {formatDate(article.publishedAt)}
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="size-4" />
              {article.readTimeMinutes} min read
            </span>
          </div>
        </div>
      </div>

      <div className="mx-auto mt-6 max-w-5xl px-4 sm:px-6 lg:px-8">
        <div className="aspect-[16/9] w-full overflow-hidden rounded-xl bg-muted">
          <img
            src={article.coverImageUrl}
            alt={article.coverImageAlt}
            className="h-full w-full object-cover"
          />
        </div>
      </div>

      <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="prose-content space-y-5">
          {article.content.map((paragraph, i) => (
            <p
              key={i}
              className="text-base leading-relaxed text-foreground/90 sm:text-lg"
            >
              {paragraph}
            </p>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap gap-2">
          {article.tags.map((tag) => (
            <Badge key={tag} variant="secondary">
              #{tag}
            </Badge>
          ))}
        </div>

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
              article.title,
            )}`}
          >
            <FaXTwitter className="size-4" />
          </ShareButton>
          <ShareButton
            label="Copy link"
            onClick={() => {
              if (typeof navigator !== "undefined" && navigator.clipboard) {
                navigator.clipboard.writeText(window.location.href)
              }
            }}
          >
            <Link2 className="size-4" />
          </ShareButton>
        </div>
      </div>

      {related.length > 0 && (
        <div className="border-t bg-muted/30">
          <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
            <SectionHeading eyebrow={category?.name} title="Related Stories" />
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {related.map((a) => (
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

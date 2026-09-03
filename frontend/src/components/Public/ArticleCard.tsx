import { Link } from "@tanstack/react-router"
import { Clock } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { calculateReadTime, formatShortDate } from "@/utils"
import { cn } from "@/lib/utils"

export interface ArticleItemData {
  id: string | number
  headline?: string
  title?: string
  slug: string
  excerpt?: string | null
  cover_image_url?: string | null
  coverImageUrl?: string
  coverImageAlt?: string
  category?: any
  category_name?: string
  author?: any
  author_name?: string
  date_published?: string | null
  publishedAt?: string
  body?: string | null
  content?: string[] | string
  readTimeMinutes?: number
}

interface ArticleCardProps {
  article: ArticleItemData
  variant?: "default" | "horizontal" | "compact" | "hero"
  className?: string
}

export function ArticleCard({
  article,
  variant = "default",
  className,
}: ArticleCardProps) {
  const title = article.headline || article.title || "Untitled Story"
  const excerpt = article.excerpt || ""
  const coverUrl =
    article.cover_image_url ||
    article.coverImageUrl ||
    "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=800&auto=format&fit=crop&q=80"
  const publishedDate = article.date_published || article.publishedAt
  const categoryName =
    typeof article.category === "object" && article.category !== null
      ? article.category.name
      : typeof article.category === "string"
      ? article.category
      : article.category_name || "News"
  const authorName =
    typeof article.author === "object" && article.author !== null
      ? article.author.full_name || article.author.name || "Eagle Eye Staff"
      : typeof article.author === "string"
      ? article.author
      : article.author_name || "Eagle Eye Staff"
  const readTime =
    article.readTimeMinutes ||
    calculateReadTime(
      typeof article.content === "string"
        ? article.content
        : article.body || excerpt
    )

  if (variant === "hero") {
    return (
      <Link
        to="/news/$slug"
        params={{ slug: article.slug }}
        className={cn(
          "group relative block overflow-hidden rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          className,
        )}
      >
        <div className="aspect-[16/9] w-full overflow-hidden bg-muted sm:aspect-[21/9]">
          <img
            src={coverUrl}
            alt={title}
            loading="eager"
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        </div>
        <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/30 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 p-5 sm:p-8">
          {categoryName && (
            <Badge className="mb-3 bg-primary text-primary-foreground">
              {categoryName}
            </Badge>
          )}
          <h2 className="max-w-3xl text-balance font-serif text-xl font-bold leading-tight text-white sm:text-3xl md:text-4xl">
            {title}
          </h2>
          {excerpt && (
            <p className="mt-2 hidden max-w-2xl text-sm text-white/80 sm:block sm:text-base line-clamp-2">
              {excerpt}
            </p>
          )}
          <div className="mt-3 flex items-center gap-2 text-xs text-white/70 sm:text-sm">
            <span>{authorName}</span>
            <span aria-hidden>&middot;</span>
            <span>{formatShortDate(publishedDate)}</span>
            <span aria-hidden>&middot;</span>
            <span className="flex items-center gap-1">
              <Clock className="size-3.5" /> {readTime} min read
            </span>
          </div>
        </div>
      </Link>
    )
  }

  if (variant === "horizontal") {
    return (
      <Link
        to="/news/$slug"
        params={{ slug: article.slug }}
        className={cn(
          "group flex gap-4 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          className,
        )}
      >
        <div className="aspect-[4/3] w-28 shrink-0 overflow-hidden rounded-md bg-muted sm:w-36">
          <img
            src={coverUrl}
            alt={title}
            loading="lazy"
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        </div>
        <div className="flex min-w-0 flex-col justify-center">
          {categoryName && (
            <span className="text-xs font-semibold uppercase tracking-wide text-primary">
              {categoryName}
            </span>
          )}
          <h3 className="mt-1 line-clamp-2 font-serif text-base font-semibold leading-snug text-foreground group-hover:text-primary sm:text-lg">
            {title}
          </h3>
          <div className="mt-1.5 flex items-center gap-2 text-xs text-muted-foreground">
            <span>{formatShortDate(publishedDate)}</span>
            <span aria-hidden>&middot;</span>
            <span>{readTime} min read</span>
          </div>
        </div>
      </Link>
    )
  }

  if (variant === "compact") {
    return (
      <Link
        to="/news/$slug"
        params={{ slug: article.slug }}
        className={cn(
          "group flex items-start gap-3 rounded-lg py-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          className,
        )}
      >
        <span className="mt-0.5 font-serif text-2xl font-bold text-muted-foreground/40 group-hover:text-primary">
          #
        </span>
        <div className="min-w-0">
          <h3 className="line-clamp-2 text-sm font-semibold leading-snug text-foreground group-hover:text-primary">
            {title}
          </h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {formatShortDate(publishedDate)}
          </p>
        </div>
      </Link>
    )
  }

  return (
    <Link
      to="/news/$slug"
      params={{ slug: article.slug }}
      className={cn(
        "group flex h-full flex-col overflow-hidden rounded-xl border bg-card transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
    >
      <div className="aspect-[16/10] w-full overflow-hidden bg-muted">
        <img
          src={coverUrl}
          alt={title}
          loading="lazy"
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
        />
      </div>
      <div className="flex flex-1 flex-col p-4 sm:p-5">
        {categoryName && (
          <span className="text-xs font-semibold uppercase tracking-wide text-primary">
            {categoryName}
          </span>
        )}
        <h3 className="mt-1.5 line-clamp-2 font-serif text-lg font-semibold leading-snug text-foreground group-hover:text-primary">
          {title}
        </h3>
        {excerpt && (
          <p className="mt-2 line-clamp-2 flex-1 text-sm text-muted-foreground">
            {excerpt}
          </p>
        )}
        <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
          <span className="font-medium text-foreground/80">{authorName}</span>
          <span aria-hidden>&middot;</span>
          <span>{formatShortDate(publishedDate)}</span>
          <span aria-hidden>&middot;</span>
          <span className="flex items-center gap-1">
            <Clock className="size-3.5" /> {readTime} min
          </span>
        </div>
      </div>
    </Link>
  )
}

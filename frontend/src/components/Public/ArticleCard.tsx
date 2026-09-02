import { Link } from "@tanstack/react-router"
import { Clock } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import type { Article } from "@/data/mockNews"
import { formatShortDate, getCategoryBySlug } from "@/data/mockNews"
import { cn } from "@/lib/utils"

interface ArticleCardProps {
  article: Article
  variant?: "default" | "horizontal" | "compact" | "hero"
  className?: string
}

export function ArticleCard({
  article,
  variant = "default",
  className,
}: ArticleCardProps) {
  const category = getCategoryBySlug(article.category)

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
            src={article.coverImageUrl}
            alt={article.coverImageAlt}
            loading="eager"
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        </div>
        <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/30 to-transparent" />
        <div className="absolute inset-x-0 bottom-0 p-5 sm:p-8">
          {category && (
            <Badge className="mb-3 bg-primary text-primary-foreground">
              {category.name}
            </Badge>
          )}
          <h2 className="max-w-3xl text-balance font-serif text-xl font-bold leading-tight text-white sm:text-3xl md:text-4xl">
            {article.title}
          </h2>
          <p className="mt-2 hidden max-w-2xl text-sm text-white/80 sm:block sm:text-base">
            {article.excerpt}
          </p>
          <div className="mt-3 flex items-center gap-2 text-xs text-white/70 sm:text-sm">
            <span>{article.author.name}</span>
            <span aria-hidden>&middot;</span>
            <span>{formatShortDate(article.publishedAt)}</span>
            <span aria-hidden>&middot;</span>
            <span className="flex items-center gap-1">
              <Clock className="size-3.5" /> {article.readTimeMinutes} min read
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
            src={article.coverImageUrl}
            alt={article.coverImageAlt}
            loading="lazy"
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        </div>
        <div className="flex min-w-0 flex-col justify-center">
          {category && (
            <span className="text-xs font-semibold uppercase tracking-wide text-primary">
              {category.name}
            </span>
          )}
          <h3 className="mt-1 line-clamp-2 font-serif text-base font-semibold leading-snug text-foreground group-hover:text-primary sm:text-lg">
            {article.title}
          </h3>
          <div className="mt-1.5 flex items-center gap-2 text-xs text-muted-foreground">
            <span>{formatShortDate(article.publishedAt)}</span>
            <span aria-hidden>&middot;</span>
            <span>{article.readTimeMinutes} min read</span>
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
          {String(article.id).padStart(2, "0")}
        </span>
        <div className="min-w-0">
          <h3 className="line-clamp-2 text-sm font-semibold leading-snug text-foreground group-hover:text-primary">
            {article.title}
          </h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {formatShortDate(article.publishedAt)}
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
          src={article.coverImageUrl}
          alt={article.coverImageAlt}
          loading="lazy"
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
        />
      </div>
      <div className="flex flex-1 flex-col p-4 sm:p-5">
        {category && (
          <span className="text-xs font-semibold uppercase tracking-wide text-primary">
            {category.name}
          </span>
        )}
        <h3 className="mt-1.5 line-clamp-2 font-serif text-lg font-semibold leading-snug text-foreground group-hover:text-primary">
          {article.title}
        </h3>
        <p className="mt-2 line-clamp-2 flex-1 text-sm text-muted-foreground">
          {article.excerpt}
        </p>
        <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
          <span className="font-medium text-foreground/80">
            {article.author.name}
          </span>
          <span aria-hidden>&middot;</span>
          <span>{formatShortDate(article.publishedAt)}</span>
          <span aria-hidden>&middot;</span>
          <span className="flex items-center gap-1">
            <Clock className="size-3.5" /> {article.readTimeMinutes} min
          </span>
        </div>
      </div>
    </Link>
  )
}

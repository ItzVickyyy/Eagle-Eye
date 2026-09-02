import { createFileRoute, Link } from "@tanstack/react-router"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { z } from "zod"

import { ArticleCard } from "@/components/Public/ArticleCard"
import { EmptyState } from "@/components/Public/States"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import {
  Pagination,
  PaginationContent,
  PaginationItem,
} from "@/components/ui/pagination"
import { categories, getArticleList, getCategoryBySlug } from "@/data/mockNews"
import { cn } from "@/lib/utils"

const newsSearchSchema = z.object({
  category: z.string().optional().catch(undefined),
  page: z.number().int().min(1).optional().catch(1),
})

export const Route = createFileRoute("/_public/news/")({
  component: NewsListing,
  validateSearch: newsSearchSchema,
  head: ({ match }) => {
    const category = getCategoryBySlug(match.search.category ?? "")
    return {
      meta: [
        {
          title: category ? `${category.name} - Eagle Eye` : "News - Eagle Eye",
        },
      ],
    }
  },
})

const PAGE_SIZE = 9

function NewsListing() {
  const { category: categorySlug, page = 1 } = Route.useSearch()
  const activeCategory = categorySlug
    ? getCategoryBySlug(categorySlug)
    : undefined

  const {
    items,
    total,
    totalPages,
    page: currentPage,
  } = getArticleList({
    category: categorySlug,
    page,
    pageSize: PAGE_SIZE,
  })

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-wider text-primary">
          {activeCategory ? activeCategory.name : "All Stories"}
        </p>
        <h1 className="mt-1 font-serif text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          {activeCategory ? activeCategory.name : "Latest News"}
        </h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          {activeCategory
            ? activeCategory.description
            : "Every story published by the Eagle Eye newsroom, most recent first."}
        </p>
      </div>

      {/* Category filter pills */}
      <div className="mb-8 flex flex-wrap gap-2">
        <Link
          to="/news"
          className={cn(
            "inline-flex items-center rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors hover:bg-accent",
            !activeCategory &&
              "border-primary bg-primary text-primary-foreground hover:bg-primary/90",
          )}
        >
          All
        </Link>
        {categories.map((c) => (
          <Link
            key={c.slug}
            to="/news"
            search={{ category: c.slug }}
            className={cn(
              "inline-flex items-center rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors hover:bg-accent",
              activeCategory?.slug === c.slug &&
                "border-primary bg-primary text-primary-foreground hover:bg-primary/90",
            )}
          >
            {c.name}
          </Link>
        ))}
      </div>

      {total > 0 && (
        <p className="mb-4 text-sm text-muted-foreground">
          Showing {items.length} of {total} {total === 1 ? "story" : "stories"}
        </p>
      )}

      {items.length === 0 ? (
        <EmptyState
          title="No stories in this category yet"
          description="New articles are published regularly — check back soon or explore another category."
          action={
            <Badge variant="secondary" className="px-3 py-1">
              More coming soon
            </Badge>
          }
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>

          {totalPages > 1 && (
            <div className="mt-10">
              <Pagination>
                <PaginationContent>
                  <PaginationItem>
                    <Link
                      to="/news"
                      search={{
                        category: categorySlug,
                        page: Math.max(1, currentPage - 1),
                      }}
                      aria-label="Go to previous page"
                      aria-disabled={currentPage <= 1}
                      className={cn(
                        buttonVariants({ variant: "ghost" }),
                        "gap-1 px-2.5",
                        currentPage <= 1 && "pointer-events-none opacity-40",
                      )}
                    >
                      <ChevronLeft className="size-4" />
                      <span className="hidden sm:block">Previous</span>
                    </Link>
                  </PaginationItem>
                  {Array.from({ length: totalPages }).map((_, i) => {
                    const pageNum = i + 1
                    const isActive = pageNum === currentPage
                    return (
                      <PaginationItem key={pageNum}>
                        <Link
                          to="/news"
                          search={{ category: categorySlug, page: pageNum }}
                          aria-current={isActive ? "page" : undefined}
                          className={cn(
                            buttonVariants({
                              variant: isActive ? "outline" : "ghost",
                              size: "icon",
                            }),
                          )}
                        >
                          {pageNum}
                        </Link>
                      </PaginationItem>
                    )
                  })}
                  <PaginationItem>
                    <Link
                      to="/news"
                      search={{
                        category: categorySlug,
                        page: Math.min(totalPages, currentPage + 1),
                      }}
                      aria-label="Go to next page"
                      aria-disabled={currentPage >= totalPages}
                      className={cn(
                        buttonVariants({ variant: "ghost" }),
                        "gap-1 px-2.5",
                        currentPage >= totalPages &&
                          "pointer-events-none opacity-40",
                      )}
                    >
                      <span className="hidden sm:block">Next</span>
                      <ChevronRight className="size-4" />
                    </Link>
                  </PaginationItem>
                </PaginationContent>
              </Pagination>
            </div>
          )}
        </>
      )}
    </div>
  )
}

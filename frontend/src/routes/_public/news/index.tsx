import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { z } from "zod"

import { ArticlesService, CategoriesService } from "@/client"
import { ArticleCard } from "@/components/Public/ArticleCard"
import { EmptyState, LoadingState } from "@/components/Public/States"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import {
  Pagination,
  PaginationContent,
  PaginationItem,
} from "@/components/ui/pagination"
import { cn } from "@/lib/utils"

const newsSearchSchema = z.object({
  category: z.string().optional().catch(undefined),
  page: z.number().int().min(1).optional().catch(1),
})

export const Route = createFileRoute("/_public/news/")({
  component: NewsListing,
  validateSearch: newsSearchSchema,
  head: ({ match }) => ({
    meta: [
      {
        title: match.search.category
          ? `${match.search.category.toUpperCase()} - Eagle Eye`
          : "News Archive - Eagle Eye",
      },
    ],
  }),
})

const PAGE_SIZE = 9

function NewsListing() {
  const { category: categorySlug, page = 1 } = Route.useSearch()

  const { data: categoriesRes } = useQuery({
    queryKey: ["public-categories"],
    queryFn: () => CategoriesService.readCategories({ query: { limit: 50 } }),
  })

  const categories: any[] = (categoriesRes?.data as any)?.data || (categoriesRes as any)?.data || []
  const activeCategory = categories.find((c) => c.slug === categorySlug)

  const { data: articlesRes, isLoading } = useQuery({
    queryKey: ["public-articles", categorySlug, page],
    queryFn: () =>
      ArticlesService.readArticles({
        query: {
          category_slug: categorySlug,
          skip: (page - 1) * PAGE_SIZE,
          limit: PAGE_SIZE,
        },
      }),
  })

  const articles: any[] = (articlesRes?.data as any)?.data || (articlesRes as any)?.data || []
  const total = (articlesRes?.data as any)?.count ?? (articlesRes as any)?.count ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE) || 1

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
          {activeCategory?.description ||
            "Every story published by the Eagle Eye newsroom, most recent first."}
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

      {isLoading ? (
        <LoadingState />
      ) : articles.length === 0 ? (
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
          <p className="mb-4 text-sm text-muted-foreground">
            Showing {articles.length} of {total} {total === 1 ? "story" : "stories"}
          </p>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {articles.map((article) => (
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
                        page: Math.max(1, page - 1),
                      }}
                      aria-label="Go to previous page"
                      aria-disabled={page <= 1}
                      className={cn(
                        buttonVariants({ variant: "ghost" }),
                        "gap-1 px-2.5",
                        page <= 1 && "pointer-events-none opacity-40",
                      )}
                    >
                      <ChevronLeft className="size-4" />
                      <span className="hidden sm:block">Previous</span>
                    </Link>
                  </PaginationItem>
                  {Array.from({ length: totalPages }).map((_, i) => {
                    const pageNum = i + 1
                    const isActive = pageNum === page
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
                        page: Math.min(totalPages, page + 1),
                      }}
                      aria-label="Go to next page"
                      aria-disabled={page >= totalPages}
                      className={cn(
                        buttonVariants({ variant: "ghost" }),
                        "gap-1 px-2.5",
                        page >= totalPages &&
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

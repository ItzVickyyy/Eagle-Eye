import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Search as SearchIcon } from "lucide-react"
import { useState } from "react"
import { z } from "zod"

import { ArticlesService } from "@/client"
import { ArticleCard } from "@/components/Public/ArticleCard"
import { EmptyState, LoadingState, SearchEmptyState } from "@/components/Public/States"
import { Button } from "@/components/ui/button"

const searchParamsSchema = z.object({
  q: z.string().optional().catch(undefined),
})

export const Route = createFileRoute("/_public/search")({
  component: SearchResults,
  validateSearch: searchParamsSchema,
  head: ({ match }) => ({
    meta: [
      {
        title: match.search.q
          ? `Search: ${match.search.q} - Eagle Eye`
          : "Search - Eagle Eye",
      },
    ],
  }),
})

function SearchResults() {
  const { q } = Route.useSearch()
  const navigate = Route.useNavigate()
  const [draft, setDraft] = useState(q ?? "")

  const { data: searchResults, isLoading } = useQuery({
    queryKey: ["search-articles", q],
    queryFn: () =>
      ArticlesService.readArticles({
        query: {
          search: q?.trim(),
          limit: 24,
        },
      }),
    enabled: !!q && q.trim().length > 0,
  })

  const results: any[] = (searchResults as any)?.data?.data || (searchResults as any)?.data || []
  const total: number = (searchResults as any)?.data?.count ?? (searchResults as any)?.count ?? 0

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = draft.trim()
    navigate({ search: trimmed ? { q: trimmed } : {} })
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="font-serif text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
        Search
      </h1>
      <p className="mt-2 text-muted-foreground">
        Search Eagle Eye's archive across headline, body text, and topics.
      </p>

      <form onSubmit={onSubmit} className="mt-6 flex gap-2">
        <div className="relative flex-1">
          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Search articles, authors, or topics..."
            aria-label="Search articles"
            className="h-11 w-full rounded-md border bg-background pl-9 pr-3 text-sm shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
          />
        </div>
        <Button type="submit" size="lg">
          Search
        </Button>
      </form>

      <div className="mt-10">
        {!q && (
          <EmptyState
            icon={<SearchIcon className="size-6" />}
            title="Start typing to search"
            description="Try searching for a topic like “championship”, “academics”, or “facilities”."
          />
        )}

        {q && isLoading && <LoadingState />}

        {q && !isLoading && total === 0 && <SearchEmptyState query={q} />}

        {q && !isLoading && total > 0 && (
          <>
            <p className="mb-5 text-sm text-muted-foreground">
              {total} {total === 1 ? "result" : "results"} for &ldquo;{q}&rdquo;
            </p>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {results.map((article) => (
                <ArticleCard key={article.id} article={article} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

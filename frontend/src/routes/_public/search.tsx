import { createFileRoute } from "@tanstack/react-router"
import { Search as SearchIcon } from "lucide-react"
import { useState } from "react"
import { z } from "zod"

import { ArticleCard } from "@/components/Public/ArticleCard"
import { EmptyState, SearchEmptyState } from "@/components/Public/States"
import { Button } from "@/components/ui/button"
import { searchArticles } from "@/data/mockNews"

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

  const results = q ? searchArticles(q, { pageSize: 24 }) : undefined

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
        Search Eagle Eye's archive by headline, topic, or author.
      </p>

      <form onSubmit={onSubmit} className="mt-6 flex gap-2">
        <div className="relative flex-1">
          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Search articles, authors, or topics…"
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
            description="Try searching for a topic like “basketball,” “robotics,” or a staff writer's name."
          />
        )}

        {q && results && results.total === 0 && <SearchEmptyState query={q} />}

        {q && results && results.total > 0 && (
          <>
            <p className="mb-5 text-sm text-muted-foreground">
              {results.total} {results.total === 1 ? "result" : "results"} for
              &ldquo;{q}&rdquo;
            </p>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {results.items.map((article) => (
                <ArticleCard key={article.id} article={article} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

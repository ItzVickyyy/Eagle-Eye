import { createFileRoute, Link } from "@tanstack/react-router"
import { FileText, PlusCircle } from "lucide-react"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/admin/articles")({
  component: Articles,
  head: () => ({
    meta: [{ title: "Articles — Eagle Eye" }],
  }),
})

function Articles() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Articles</h1>
          <p className="text-muted-foreground">
            Create and manage your articles
          </p>
        </div>
        <Button asChild>
          <Link to="/admin/articles/new">
            <PlusCircle className="mr-2 size-4" />
            New Article
          </Link>
        </Button>
      </div>

      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
        <div className="rounded-full bg-muted p-4 mb-4">
          <FileText className="size-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">No articles yet</h3>
        <p className="mt-1 text-muted-foreground text-sm max-w-xs">
          The article management API is coming soon. Create your first article
          to get started.
        </p>
        <Button asChild className="mt-6">
          <Link to="/admin/articles/new">Write your first article</Link>
        </Button>
      </div>
    </div>
  )
}

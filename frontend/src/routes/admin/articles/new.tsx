import { createFileRoute, Link } from "@tanstack/react-router"

import { ArrowLeft, FileEdit } from "lucide-react"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/admin/articles/new")({
  component: NewArticle,
  head: () => ({
    meta: [{ title: "New Article — Eagle Eye" }],
  }),
})

function NewArticle() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-4">
        <Button asChild variant="ghost" size="icon">
          <Link to="/admin/articles">
            <ArrowLeft className="size-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">New Article</h1>
          <p className="text-muted-foreground">
            Draft a new article for the Eagle Eye newsroom
          </p>
        </div>
      </div>

      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
        <div className="rounded-full bg-muted p-4 mb-4">
          <FileEdit className="size-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">Rich text editor</h3>
        <p className="mt-1 text-muted-foreground text-sm max-w-xs">
          The article editor with rich text (TipTap), cover image upload, tags,
          and category selection is coming soon.
        </p>
      </div>
    </div>
  )
}

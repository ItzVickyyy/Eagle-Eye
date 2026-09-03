import { createFileRoute } from "@tanstack/react-router"

import { ListChecks } from "lucide-react"

export const Route = createFileRoute("/admin/review-queue")({
  component: ReviewQueue,
  head: () => ({
    meta: [{ title: "Review Queue — Eagle Eye" }],
  }),
})

function ReviewQueue() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Review Queue</h1>
        <p className="text-muted-foreground">
          Articles submitted for editorial review
        </p>
      </div>

      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
        <div className="rounded-full bg-muted p-4 mb-4">
          <ListChecks className="size-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">Queue is empty</h3>
        <p className="mt-1 text-muted-foreground text-sm max-w-xs">
          Articles submitted for review will appear here. The review workflow
          API is coming soon.
        </p>
      </div>
    </div>
  )
}

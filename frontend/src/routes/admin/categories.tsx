import { createFileRoute, redirect } from "@tanstack/react-router"

import { Layers } from "lucide-react"
import { UsersService } from "@/client"

export const Route = createFileRoute("/admin/categories")({
  component: Categories,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({ to: "/admin" })
    }
  },
  head: () => ({
    meta: [{ title: "Categories — Eagle Eye" }],
  }),
})

function Categories() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Categories</h1>
        <p className="text-muted-foreground">
          Manage article categories and tags
        </p>
      </div>

      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Layers className="size-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">Categories management</h3>
        <p className="mt-1 text-muted-foreground text-sm max-w-xs">
          Create and edit article categories (News, Academics, Sports, Events)
          and tags. The categories API is coming soon.
        </p>
      </div>
    </div>
  )
}

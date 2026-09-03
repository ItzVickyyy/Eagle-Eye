import { createFileRoute, redirect } from "@tanstack/react-router"

import { Users } from "lucide-react"
import { UsersService } from "@/client"

export const Route = createFileRoute("/admin/members")({
  component: Members,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({ to: "/admin" })
    }
  },
  head: () => ({
    meta: [{ title: "Club Members — Eagle Eye" }],
  }),
})

function Members() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Club Members</h1>
        <p className="text-muted-foreground">
          Manage the About Us page — advisers, officers, and members
        </p>
      </div>

      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Users className="size-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">Club member management</h3>
        <p className="mt-1 text-muted-foreground text-sm max-w-xs">
          Add, edit, and organize Media Club advisers, officers, and members for
          the public About Us page. The members API is coming soon.
        </p>
      </div>
    </div>
  )
}

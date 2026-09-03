import { createFileRoute, redirect } from "@tanstack/react-router"

import { BarChart2 } from "lucide-react"
import { UsersService } from "@/client"

export const Route = createFileRoute("/admin/analytics")({
  component: Analytics,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({ to: "/admin" })
    }
  },
  head: () => ({
    meta: [{ title: "Analytics — Eagle Eye" }],
  }),
})

function Analytics() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
        <p className="text-muted-foreground">
          Article views, traffic, and readership stats
        </p>
      </div>

      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
        <div className="rounded-full bg-muted p-4 mb-4">
          <BarChart2 className="size-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">Analytics dashboard</h3>
        <p className="mt-1 text-muted-foreground text-sm max-w-xs">
          Page views, top articles, and readership trends will appear here once
          the analytics API is connected.
        </p>
      </div>
    </div>
  )
}

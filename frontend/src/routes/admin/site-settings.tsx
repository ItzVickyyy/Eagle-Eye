import { createFileRoute, redirect } from "@tanstack/react-router"

import { Settings } from "lucide-react"
import { UsersService } from "@/client"

export const Route = createFileRoute("/admin/site-settings")({
  component: SiteSettings,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({ to: "/admin" })
    }
  },
  head: () => ({
    meta: [{ title: "Site Settings — Eagle Eye" }],
  }),
})

function SiteSettings() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Site Settings</h1>
        <p className="text-muted-foreground">
          Manage the site name, logo, social links, and other global settings
        </p>
      </div>

      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Settings className="size-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">Site settings</h3>
        <p className="mt-1 text-muted-foreground text-sm max-w-xs">
          Configure the Eagle Eye site name, logo, social media links, and other
          global options. The settings API is coming soon.
        </p>
      </div>
    </div>
  )
}

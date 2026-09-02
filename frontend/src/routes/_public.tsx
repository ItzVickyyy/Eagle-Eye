import { createFileRoute, Outlet } from "@tanstack/react-router"

import { SiteFooter } from "@/components/Public/SiteFooter"
import { SiteHeader } from "@/components/Public/SiteHeader"

export const Route = createFileRoute("/_public")({
  component: PublicLayout,
})

function PublicLayout() {
  return (
    <div className="flex min-h-svh flex-col">
      <SiteHeader />
      <main className="flex-1">
        <Outlet />
      </main>
      <SiteFooter />
    </div>
  )
}

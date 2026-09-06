import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"

import { Footer } from "@/components/Common/Footer"
import AppSidebar from "@/components/Sidebar/AppSidebar"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import { UsersService } from "@/client"
import { isLoggedIn } from "@/hooks/useAuth"

const isStaffAdmin = (user: {
  is_superuser?: boolean
  role?: string | null
}) =>
  Boolean(user.is_superuser) ||
  user.role === "super_admin" ||
  user.role === "admin"

export const Route = createFileRoute("/admin")({
  component: Layout,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({
        to: "/login",
      })
    }

    let user
    try {
      user = (await UsersService.readUserMe()).data
    } catch {
      localStorage.removeItem("access_token")
      throw redirect({
        to: "/login",
      })
    }

    if (isStaffAdmin(user)) {
      return
    }

    if (user.is_developer) {
      throw redirect({
        to: "/admin/developer",
      })
    }

    throw redirect({
      to: "/",
    })
  },
})

function Layout() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-2 border-b bg-background px-4">
          <SidebarTrigger className="-ml-1 text-muted-foreground" />
        </header>
        <main className="flex-1 p-6 md:p-8">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
        <Footer />
      </SidebarInset>
    </SidebarProvider>
  )
}

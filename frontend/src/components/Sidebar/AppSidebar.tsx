import { Link as RouterLink, useRouterState } from "@tanstack/react-router"
import {
  BarChart2,
  FileText,
  Home,
  Inbox,
  Layers,
  ListChecks,
  MessageSquare,
  Settings,
  Terminal,
  Users,
} from "lucide-react"
import { SidebarAppearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"
import { User } from "./User"

interface NavItem {
  icon: React.ElementType
  title: string
  path: string
}

const editorItems: NavItem[] = [
  { icon: FileText, title: "Articles", path: "/admin/articles" },
  { icon: ListChecks, title: "Review Queue", path: "/admin/review-queue" },
]

const moderationItems: NavItem[] = [
  { icon: MessageSquare, title: "Comments", path: "/admin/comments" },
  { icon: Inbox, title: "Contact Inbox", path: "/admin/contact" },
]

const developerItems: NavItem[] = [
  { icon: Terminal, title: "System Dashboard", path: "/admin/developer" },
]

const superAdminItems: NavItem[] = [
  { icon: Layers, title: "Categories", path: "/admin/categories" },
  { icon: Users, title: "Members", path: "/admin/members" },
  { icon: Users, title: "Users", path: "/admin/users" },
  { icon: BarChart2, title: "Analytics", path: "/admin/analytics" },
  { icon: Settings, title: "Site Settings", path: "/admin/site-settings" },
]

function NavGroup({ label, items }: { label?: string; items: NavItem[] }) {
  const { isMobile, setOpenMobile } = useSidebar()
  const router = useRouterState()
  const currentPath = router.location.pathname

  return (
    <SidebarGroup>
      {label && <SidebarGroupLabel>{label}</SidebarGroupLabel>}
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => {
            const isActive =
              item.path === "/admin"
                ? currentPath === "/admin"
                : currentPath.startsWith(item.path)
            return (
              <SidebarMenuItem key={item.path}>
                <SidebarMenuButton
                  tooltip={item.title}
                  isActive={isActive}
                  asChild
                >
                  <RouterLink
                    to={item.path}
                    onClick={() => {
                      if (isMobile) setOpenMobile(false)
                    }}
                  >
                    <item.icon />
                    <span>{item.title}</span>
                  </RouterLink>
                </SidebarMenuButton>
              </SidebarMenuItem>
            )
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  )
}

export function AppSidebar() {
  const { user: currentUser } = useAuth()

  const isStaffAdmin =
    currentUser?.is_superuser ||
    currentUser?.role === "super_admin" ||
    currentUser?.role === "admin"

  const dashboardItems: NavItem[] = [
    { icon: Home, title: "Dashboard", path: "/admin" },
  ]

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Logo variant="responsive" to="/admin" />
      </SidebarHeader>
      <SidebarContent>
        <NavGroup items={dashboardItems} />
        <NavGroup label="Content" items={editorItems} />
        {isStaffAdmin && (
          <NavGroup label="Moderation & Inbox" items={moderationItems} />
        )}
        {currentUser?.is_developer && (
          <NavGroup label="Developer" items={developerItems} />
        )}
        {currentUser?.is_superuser && (
          <NavGroup label="Administration" items={superAdminItems} />
        )}
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
        <User user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar

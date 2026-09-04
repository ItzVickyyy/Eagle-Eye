import { createFileRoute, Outlet } from "@tanstack/react-router"

export const Route = createFileRoute("/admin/articles")({
  component: ArticlesLayout,
  head: () => ({
    meta: [{ title: "Articles — Eagle Eye" }],
  }),
})

function ArticlesLayout() {
  return <Outlet />
}

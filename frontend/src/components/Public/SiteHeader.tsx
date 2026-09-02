import { Link, useNavigate, useRouterState } from "@tanstack/react-router"
import { Menu, Search, X } from "lucide-react"
import { useState } from "react"

import { Appearance } from "@/components/Common/Appearance"
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { categories } from "@/data/mockNews"
import { cn } from "@/lib/utils"

const primaryNav = [
  { label: "Home", to: "/" as const },
  { label: "News", to: "/news" as const },
  { label: "About Us", to: "/about" as const },
  { label: "Contact", to: "/contact" as const },
]

export function SiteHeader() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const pathname = useRouterState({ select: (s) => s.location.pathname })

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      {/* Utility bar */}
      <div className="hidden border-b border-border/60 bg-muted/40 sm:block">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-1.5 text-xs text-muted-foreground sm:px-6 lg:px-8">
          <p>Colegio de los Baños Media Club</p>
          <p>{todayLabel()}</p>
        </div>
      </div>

      {/* Main bar */}
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2.5 shrink-0">
          <span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground font-serif text-lg font-bold">
            E
          </span>
          <span className="flex flex-col leading-tight">
            <span className="font-serif text-lg font-bold tracking-tight text-foreground">
              Eagle Eye
            </span>
            <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              CDLB Media Club
            </span>
          </span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-1 md:flex">
          {primaryNav.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground",
                (item.to === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.to)) &&
                  "bg-accent text-foreground",
              )}
            >
              {item.label}
            </Link>
          ))}
          <div className="relative ml-1 group">
            <button
              type="button"
              className="rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              Categories
            </button>
            <div className="invisible absolute right-0 top-full z-50 grid w-56 grid-cols-1 gap-0.5 rounded-md border bg-popover p-1.5 opacity-0 shadow-md transition-all group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100">
              {categories.map((c) => (
                <Link
                  key={c.slug}
                  to="/news"
                  search={{ category: c.slug }}
                  className="rounded-sm px-2.5 py-1.5 text-sm text-popover-foreground hover:bg-accent"
                >
                  {c.name}
                </Link>
              ))}
            </div>
          </div>
        </nav>

        {/* Right actions */}
        <div className="flex items-center gap-1.5">
          <SearchButton />
          <div className="hidden sm:block">
            <Appearance />
          </div>
          <Button asChild size="sm" className="hidden sm:inline-flex">
            <Link to="/login">Staff Login</Link>
          </Button>

          {/* Mobile menu */}
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="md:hidden"
                aria-label="Open menu"
              >
                <Menu className="size-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-full sm:max-w-xs">
              <SheetHeader>
                <SheetTitle className="font-serif text-lg">
                  Eagle Eye
                </SheetTitle>
              </SheetHeader>
              <nav className="flex flex-col gap-1 px-4">
                {primaryNav.map((item) => (
                  <SheetClose asChild key={item.to}>
                    <Link
                      to={item.to}
                      className={cn(
                        "rounded-md px-3 py-2.5 text-base font-medium text-foreground hover:bg-accent",
                        (item.to === "/"
                          ? pathname === "/"
                          : pathname.startsWith(item.to)) && "bg-accent",
                      )}
                    >
                      {item.label}
                    </Link>
                  </SheetClose>
                ))}
                <div className="my-2 h-px bg-border" />
                <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Categories
                </p>
                {categories.map((c) => (
                  <SheetClose asChild key={c.slug}>
                    <Link
                      to="/news"
                      search={{ category: c.slug }}
                      className="rounded-md px-3 py-2.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground"
                    >
                      {c.name}
                    </Link>
                  </SheetClose>
                ))}
                <div className="my-2 h-px bg-border" />
                <SheetClose asChild>
                  <Link
                    to="/login"
                    className="rounded-md px-3 py-2.5 text-base font-medium text-primary hover:bg-accent"
                  >
                    Staff Login
                  </Link>
                </SheetClose>
                <div className="px-3 pt-2">
                  <Appearance />
                </div>
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  )
}

function SearchButton() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [value, setValue] = useState("")

  const submit = () => {
    const q = value.trim()
    if (!q) return
    navigate({ to: "/search", search: { q } })
    setOpen(false)
    setValue("")
  }

  if (open) {
    return (
      <form
        className="flex items-center gap-1"
        onSubmit={(e) => {
          e.preventDefault()
          submit()
        }}
      >
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onBlur={() => {
            if (!value) setOpen(false)
          }}
          placeholder="Search articles…"
          className="h-9 w-36 rounded-md border bg-background px-3 text-sm shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 sm:w-52"
        />
        <Button type="submit" size="icon" variant="ghost" aria-label="Search">
          <Search className="size-4" />
        </Button>
        <Button
          type="button"
          size="icon"
          variant="ghost"
          aria-label="Close search"
          onClick={() => setOpen(false)}
        >
          <X className="size-4" />
        </Button>
      </form>
    )
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label="Search"
      onClick={() => setOpen(true)}
    >
      <Search className="size-5" />
    </Button>
  )
}

function todayLabel() {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

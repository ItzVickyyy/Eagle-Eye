import { Link } from "@tanstack/react-router"

import { cn } from "@/lib/utils"

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
  to?: string
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
  to = "/",
}: LogoProps) {
  const iconMark = (
    <span
      className={cn(
        "flex items-center justify-center rounded-md bg-primary text-primary-foreground font-serif font-bold shrink-0",
        variant === "icon" ? "size-8 text-base" : "size-9 text-lg",
        className,
      )}
    >
      E
    </span>
  )

  const fullMark = (
    <span className="flex items-center gap-2.5">
      <span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground font-serif text-lg font-bold shrink-0">
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
    </span>
  )

  const responsiveMark = (
    <>
      <span className="group-data-[collapsible=icon]:hidden">{fullMark}</span>
      <span className="hidden group-data-[collapsible=icon]:flex">
        {iconMark}
      </span>
    </>
  )

  const content =
    variant === "responsive"
      ? responsiveMark
      : variant === "icon"
        ? iconMark
        : fullMark

  if (!asLink) {
    return <>{content}</>
  }

  return <Link to={to}>{content}</Link>
}

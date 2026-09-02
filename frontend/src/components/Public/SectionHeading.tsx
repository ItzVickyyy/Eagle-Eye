import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

interface SectionHeadingProps {
  eyebrow?: string
  title: string
  action?: ReactNode
  className?: string
}

export function SectionHeading({
  eyebrow,
  title,
  action,
  className,
}: SectionHeadingProps) {
  return (
    <div
      className={cn(
        "mb-6 flex items-end justify-between gap-4 border-b pb-3",
        className,
      )}
    >
      <div>
        {eyebrow && (
          <p className="text-xs font-semibold uppercase tracking-wider text-primary">
            {eyebrow}
          </p>
        )}
        <h2 className="font-serif text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          {title}
        </h2>
      </div>
      {action}
    </div>
  )
}

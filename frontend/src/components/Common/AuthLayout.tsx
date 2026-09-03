import { Link } from "@tanstack/react-router"

import { Appearance } from "@/components/Common/Appearance"
import { Footer } from "./Footer"

interface AuthLayoutProps {
  children: React.ReactNode
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      <div className="relative hidden lg:flex lg:flex-col lg:items-center lg:justify-center bg-primary">
        <Link
          to="/"
          className="flex flex-col items-center gap-3 text-primary-foreground"
        >
          <span className="flex h-20 w-20 items-center justify-center rounded-2xl border-2 border-primary-foreground/30 bg-primary-foreground/10 font-serif text-4xl font-bold">
            E
          </span>
          <span className="flex flex-col items-center leading-tight">
            <span className="font-serif text-3xl font-bold tracking-tight">
              Eagle Eye
            </span>
            <span className="mt-1 text-sm font-medium uppercase tracking-widest opacity-80">
              CDLB Media Club
            </span>
          </span>
        </Link>
        <p className="absolute bottom-8 text-sm text-primary-foreground/60">
          Student journalism, published with purpose.
        </p>
      </div>
      <div className="flex flex-col gap-4 p-6 md:p-10">
        <div className="flex justify-end">
          <Appearance />
        </div>
        <div className="flex flex-1 items-center justify-center">
          <div className="w-full max-w-xs">{children}</div>
        </div>
        <Footer />
      </div>
    </div>
  )
}

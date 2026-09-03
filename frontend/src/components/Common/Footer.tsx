export function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="border-t py-4 px-6">
      <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
        <p className="text-muted-foreground text-sm">
          Eagle Eye — CDLB Media Club &copy; {currentYear}
        </p>
        <p className="text-muted-foreground text-xs">
          Student journalism, published with purpose.
        </p>
      </div>
    </footer>
  )
}

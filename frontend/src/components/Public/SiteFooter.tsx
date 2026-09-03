import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { Mail } from "lucide-react"
import { FaFacebookF, FaInstagram, FaXTwitter } from "react-icons/fa6"

import { CategoriesService, SettingsService } from "@/client"

const fallbackCategories = [
  { name: "News", slug: "news" },
  { name: "Academics", slug: "academics" },
  { name: "Sports", slug: "sports" },
  { name: "Events", slug: "events" },
]

export function SiteFooter() {
  const currentYear = new Date().getFullYear()

  // Fetch categories from API
  const { data: categoriesData } = useQuery({
    queryKey: ["site-categories"],
    queryFn: () => CategoriesService.readCategories({ query: { limit: 10 } }),
  })

  // Fetch site settings from API
  const { data: settingsRes } = useQuery({
    queryKey: ["public-site-settings"],
    queryFn: () => SettingsService.getSiteSettings(),
  })

  const categories: Array<{ name: string; slug: string }> =
    (categoriesData as any)?.data?.data ||
    (categoriesData as any)?.data ||
    fallbackCategories

  const settingsMap: Record<string, string> = {}
  const settingsItems: any[] =
    (settingsRes as any)?.data?.data || (settingsRes as any)?.data || []
  settingsItems.forEach((item) => {
    if (item?.key && item?.value !== undefined) {
      settingsMap[item.key] = item.value
    }
  })

  const siteName = settingsMap["site_name"] || "Eagle Eye"
  const siteTagline =
    settingsMap["site_tagline"] ||
    "The official student publication of Colegio de Los Baños, reporting campus news since day one."
  const contactEmail = settingsMap["contact_email"] || "mediaclub@cdlb.edu.ph"
  const schoolName = settingsMap["school_name"] || "Colegio de Los Baños"
  const newsroomLocation =
    settingsMap["newsroom_location"] || "Los Baños, Laguna, Philippines"
  const facebookUrl =
    settingsMap["facebook_url"] || "https://facebook.com/cdlbmediaclub"
  const twitterUrl = settingsMap["twitter_url"] || ""
  const instagramUrl = settingsMap["instagram_url"] || ""

  const socialLinks = [
    { icon: FaFacebookF, href: facebookUrl, label: "Facebook" },
    { icon: FaInstagram, href: instagramUrl || "https://instagram.com", label: "Instagram" },
    { icon: FaXTwitter, href: twitterUrl || "https://twitter.com", label: "Twitter" },
  ].filter((s) => Boolean(s.href))

  return (
    <footer className="border-t bg-muted/30">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-2 md:grid-cols-4">
          <div className="col-span-2 md:col-span-1">
            <Link to="/" className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground font-serif text-lg font-bold">
                E
              </span>
              <span className="font-serif text-lg font-bold text-foreground">
                {siteName}
              </span>
            </Link>
            <p className="mt-3 max-w-xs text-sm text-muted-foreground">
              {siteTagline}
            </p>
            <div className="mt-4 flex items-center gap-3">
              {socialLinks.map(({ icon: Icon, href, label }) => (
                <a
                  key={label}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={label}
                  className="text-muted-foreground transition-colors hover:text-primary"
                >
                  <Icon className="h-5 w-5" />
                </a>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-foreground">Sections</h3>
            <ul className="mt-3 space-y-2">
              {categories.slice(0, 5).map((c) => (
                <li key={c.slug}>
                  <Link
                    to="/news"
                    search={{ category: c.slug }}
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {c.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-foreground">The Club</h3>
            <ul className="mt-3 space-y-2">
              <li>
                <Link
                  to="/about-us"
                  className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                  About Us
                </Link>
              </li>
              <li>
                <Link
                  to="/contact-us"
                  className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                  Contact Us
                </Link>
              </li>
              <li>
                <Link
                  to="/login"
                  className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                  Staff Login
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-foreground">
              Get in Touch
            </h3>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
              <li className="flex items-center gap-2">
                <Mail className="size-4 shrink-0" />
                <a
                  href={`mailto:${contactEmail}`}
                  className="transition-colors hover:text-foreground"
                >
                  {contactEmail}
                </a>
              </li>
              <li>{schoolName}</li>
              <li>{newsroomLocation}</li>
            </ul>
          </div>
        </div>

        <div className="mt-10 flex flex-col items-center justify-between gap-3 border-t pt-6 text-xs text-muted-foreground sm:flex-row">
          <p>
            &copy; {currentYear} {siteName} &mdash; CDLB Media Club. All rights
            reserved.
          </p>
          <p>Built by student journalists, for students.</p>
        </div>
      </div>
    </footer>
  )
}

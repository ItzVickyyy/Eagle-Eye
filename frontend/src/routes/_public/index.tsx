import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowRight } from "lucide-react"

import { ArticleCard } from "@/components/Public/ArticleCard"
import { SectionHeading } from "@/components/Public/SectionHeading"
import { EmptyState } from "@/components/Public/States"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  categories,
  getArticlesByCategory,
  getFeaturedArticles,
  getLatestArticles,
} from "@/data/mockNews"

export const Route = createFileRoute("/_public/")({
  component: Home,
  head: () => ({
    meta: [
      {
        title: "Eagle Eye â€” CDLB Media Club",
      },
    ],
  }),
})

function Home() {
  const featured = getFeaturedArticles(3)
  const [heroArticle, ...secondaryFeatured] = featured
  const latest = getLatestArticles(7)
  const spotlightCategories = categories.slice(0, 3)

  if (!heroArticle) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <EmptyState
          title="No stories published yet"
          description="Check back soon â€” the Eagle Eye newsroom is just getting started."
        />
      </div>
    )
  }

  return (
    <div>
      {/* Featured / hero section */}
      <section className="mx-auto max-w-7xl px-4 pt-6 sm:px-6 sm:pt-8 lg:px-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <ArticleCard
            article={heroArticle}
            variant="hero"
            className="lg:col-span-2"
          />
          <div className="flex flex-col gap-5 rounded-xl border p-4 sm:p-5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Also making headlines
            </h3>
            <div className="flex flex-col gap-5 divide-y">
              {secondaryFeatured.length > 0 ? (
                secondaryFeatured.map((article, i) => (
                  <div key={article.id} className={i > 0 ? "pt-5" : ""}>
                    <ArticleCard article={article} variant="horizontal" />
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">
                  More stories coming soon.
                </p>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Latest news */}
      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <SectionHeading
          eyebrow="Fresh off the press"
          title="Latest News"
          action={
            <Button asChild variant="ghost" size="sm">
              <Link to="/news" className="gap-1.5">
                View all <ArrowRight className="size-4" />
              </Link>
            </Button>
          }
        />
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {latest.slice(0, 6).map((article) => (
            <ArticleCard key={article.id} article={article} />
          ))}
        </div>
      </section>

      {/* Category spotlights */}
      {spotlightCategories.map((category) => {
        const items = getArticlesByCategory(category.slug, 4)
        if (items.length === 0) return null
        return (
          <section
            key={category.slug}
            className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8"
          >
            <SectionHeading
              title={category.name}
              action={
                <Button asChild variant="ghost" size="sm">
                  <Link
                    to="/news"
                    search={{ category: category.slug }}
                    className="gap-1.5"
                  >
                    More {category.name} <ArrowRight className="size-4" />
                  </Link>
                </Button>
              }
            />
            <div className="grid grid-cols-1 gap-x-8 gap-y-4 sm:grid-cols-2">
              {items.map((article) => (
                <ArticleCard
                  key={article.id}
                  article={article}
                  variant="horizontal"
                />
              ))}
            </div>
          </section>
        )
      })}

      {/* About strip */}
      <section className="border-t bg-muted/30">
        <div className="mx-auto grid max-w-7xl grid-cols-1 items-center gap-8 px-4 py-14 sm:px-6 lg:grid-cols-3 lg:px-8">
          <div className="lg:col-span-2">
            <Badge variant="secondary" className="mb-3">
              About the club
            </Badge>
            <h2 className="font-serif text-2xl font-bold tracking-tight sm:text-3xl">
              Student journalism, published with purpose.
            </h2>
            <p className="mt-3 max-w-2xl text-muted-foreground">
              Eagle Eye is the official student-run publication of Colegio de
              los BaÃ±os, covering campus news, academics, sports, and student
              life â€” written, edited, and photographed entirely by CDLB
              students.
            </p>
          </div>
          <div className="flex lg:justify-end">
            <Button asChild size="lg">
              <Link to="/about-us">Meet the team</Link>
            </Button>
          </div>
        </div>
      </section>
    </div>
  )
}

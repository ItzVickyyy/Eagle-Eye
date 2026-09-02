import { createFileRoute } from "@tanstack/react-router"
import { BookOpen, Camera, PenLine, Target } from "lucide-react"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"

export const Route = createFileRoute("/_public/about")({
  component: AboutPage,
  head: () => ({
    meta: [{ title: "About Us - Eagle Eye" }],
  }),
})

const values = [
  {
    icon: PenLine,
    title: "Accurate Reporting",
    description:
      "Every story is fact-checked and reviewed before publication, holding ourselves to professional journalistic standards.",
  },
  {
    icon: Target,
    title: "Student Perspective",
    description:
      "We cover the stories that matter most to the CDLB community, told by the students who live them.",
  },
  {
    icon: Camera,
    title: "Visual Storytelling",
    description:
      "From photojournalism to layout design, we believe a story is told as much through images as words.",
  },
  {
    icon: BookOpen,
    title: "Media Literacy",
    description:
      "We aim to model responsible journalism and help our readers think critically about the news they consume.",
  },
]

const team = [
  { name: "Mari Santos", role: "Editor-in-Chief" },
  { name: "JC Dela Peña", role: "Sports Editor" },
  { name: "Alex Villanueva", role: "Arts Correspondent" },
  { name: "Sam Ocampo", role: "Opinion Columnist" },
  { name: "Kit Fernandez", role: "News Reporter" },
  { name: "Ren Bautista", role: "Staff Writer" },
]

function AboutPage() {
  return (
    <div>
      <section className="border-b bg-muted/30">
        <div className="mx-auto max-w-4xl px-4 py-16 text-center sm:px-6 lg:px-8">
          <Badge variant="secondary" className="mb-4">
            About Eagle Eye
          </Badge>
          <h1 className="font-serif text-3xl font-bold tracking-tight text-foreground sm:text-5xl">
            The student voice of Colegio de los Baños
          </h1>
          <p className="mt-4 text-lg text-muted-foreground">
            Eagle Eye is the official, student-run news publication of CDLB —
            reporting campus news, academics, sports, and student life since our
            founding.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-4xl px-4 py-14 sm:px-6 lg:px-8">
        <h2 className="font-serif text-2xl font-bold tracking-tight text-foreground">
          Our Mission
        </h2>
        <p className="mt-4 text-muted-foreground">
          The CDLB Media Club exists to inform, engage, and represent our school
          community through honest, well-researched student journalism. We train
          the next generation of writers, photographers, and editors while
          giving every student a window into campus life — from big wins on the
          court to the quiet, everyday stories that make CDLB what it is.
        </p>
        <p className="mt-4 text-muted-foreground">
          Every article on Eagle Eye is written, edited, photographed, and laid
          out entirely by CDLB students, with guidance from our faculty
          moderator.
        </p>
      </section>

      <section className="border-y bg-muted/30">
        <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6 lg:px-8">
          <h2 className="text-center font-serif text-2xl font-bold tracking-tight text-foreground">
            What We Stand For
          </h2>
          <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {values.map(({ icon: Icon, title, description }) => (
              <div
                key={title}
                className="rounded-xl border bg-card p-5 text-center"
              >
                <div className="mx-auto flex size-11 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <Icon className="size-5" />
                </div>
                <h3 className="mt-4 font-semibold text-foreground">{title}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground">
                  {description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-14 sm:px-6 lg:px-8">
        <h2 className="text-center font-serif text-2xl font-bold tracking-tight text-foreground">
          Meet the Team
        </h2>
        <p className="mx-auto mt-2 max-w-xl text-center text-muted-foreground">
          The staff behind this year's issues of Eagle Eye.
        </p>
        <div className="mt-10 grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-6">
          {team.map((member) => {
            const initials = member.name
              .split(" ")
              .map((n) => n[0])
              .join("")
            return (
              <div
                key={member.name}
                className="flex flex-col items-center text-center"
              >
                <Avatar className="size-16">
                  <AvatarFallback className="text-base font-semibold">
                    {initials}
                  </AvatarFallback>
                </Avatar>
                <p className="mt-3 text-sm font-semibold text-foreground">
                  {member.name}
                </p>
                <p className="text-xs text-muted-foreground">{member.role}</p>
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}

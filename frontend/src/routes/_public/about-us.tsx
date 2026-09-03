import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { BookOpen, Camera, PenLine, Target } from "lucide-react"

import { ClubMembersService } from "@/client"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { getInitials } from "@/utils"

export const Route = createFileRoute("/_public/about-us")({
  component: AboutPage,
  head: () => ({
    meta: [{ title: "About Us — Eagle Eye" }],
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

function AboutPage() {
  const { data: membersRes } = useQuery({
    queryKey: ["active-club-members"],
    queryFn: () => ClubMembersService.membersReadActiveMembers(),
  })

  const members: any[] = (membersRes as any)?.data?.data || (membersRes as any)?.data || []
  const advisers = members.filter(
    (m: any) =>
      m.position?.toLowerCase().includes("adviser") ||
      m.position_title?.toLowerCase().includes("adviser"),
  )
  const studentOfficers = members.filter(
    (m: any) =>
      !m.position?.toLowerCase().includes("adviser") &&
      !m.position_title?.toLowerCase().includes("adviser"),
  )

  return (
    <div>
      <section className="border-b bg-muted/30">
        <div className="mx-auto max-w-4xl px-4 py-16 text-center sm:px-6 lg:px-8">
          <Badge variant="secondary" className="mb-4">
            About Eagle Eye
          </Badge>
          <h1 className="font-serif text-3xl font-bold tracking-tight text-foreground sm:text-5xl">
            The student voice of Colegio de Los Baños
          </h1>
          <p className="mt-4 text-lg text-muted-foreground">
            Eagle Eye is the official, student-run news publication of CDLB —
            reporting campus news, academics, sports, and student life since our
            founding on May 4, 2023.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-4xl px-4 py-14 sm:px-6 lg:px-8">
        <h2 className="font-serif text-2xl font-bold tracking-tight text-foreground">
          Our Mission & History
        </h2>
        <p className="mt-4 text-muted-foreground leading-relaxed">
          The CDLB Media Club was established through the HUMSS Department after
          delegates attended the prestigious Gandingan Awards. Recognizing the
          need for a centralized, modern publication for Colegio de Los Baños,
          the club partnered with organizations from the University of the
          Philippines Los Baños (such as UPLB Jocks for broadcasting and UPLB
          Times for journalism) to build high-standard media practices.
        </p>
        <p className="mt-4 text-muted-foreground leading-relaxed">
          Every article on Eagle Eye is written, edited, photographed, and laid
          out entirely by CDLB students across our Editorial, Multimedia,
          Broadcasting, and Social Media departments, with guidance from our
          faculty advisers.
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

      {/* Meet the Team */}
      <section className="mx-auto max-w-6xl px-4 py-14 sm:px-6 lg:px-8">
        <h2 className="text-center font-serif text-2xl font-bold tracking-tight text-foreground">
          Meet the Staff & Advisers
        </h2>
        <p className="mx-auto mt-2 max-w-xl text-center text-muted-foreground">
          The dedicated student journalists and mentors behind Eagle Eye.
        </p>

        {advisers.length > 0 && (
          <div className="mt-10">
            <h3 className="text-center font-semibold text-xs uppercase tracking-wider text-primary mb-6">
              Club Advisers
            </h3>
            <div className="flex flex-wrap justify-center gap-8">
              {advisers.map((member: any) => {
                const fullName = `${member.first_name} ${member.last_name}`
                const initials = getInitials(fullName)
                return (
                  <div
                    key={member.id}
                    className="flex flex-col items-center text-center max-w-[160px]"
                  >
                    <Avatar className="size-20 border-2 border-primary/20">
                      {member.photo_url && (
                        <AvatarImage
                          src={member.photo_url}
                          alt={fullName}
                          className="object-cover"
                        />
                      )}
                      <AvatarFallback className="text-lg font-semibold bg-primary/10 text-primary">
                        {initials}
                      </AvatarFallback>
                    </Avatar>
                    <p className="mt-3 text-sm font-semibold text-foreground">
                      {fullName}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {member.position_title || member.position || "Adviser"}
                    </p>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {studentOfficers.length > 0 && (
          <div className="mt-12">
            <h3 className="text-center font-semibold text-xs uppercase tracking-wider text-primary mb-6">
              Editorial & Production Board
            </h3>
            <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-4 justify-items-center">
              {studentOfficers.map((member: any) => {
                const fullName = `${member.first_name} ${member.last_name}`
                const initials = getInitials(fullName)
                return (
                  <div
                    key={member.id}
                    className="flex flex-col items-center text-center w-full max-w-[180px] p-4 rounded-xl border bg-card/60"
                  >
                    <Avatar className="size-16">
                      {member.photo_url && (
                        <AvatarImage
                          src={member.photo_url}
                          alt={fullName}
                          className="object-cover"
                        />
                      )}
                      <AvatarFallback className="text-base font-semibold bg-muted">
                        {initials}
                      </AvatarFallback>
                    </Avatar>
                    <p className="mt-3 text-sm font-semibold text-foreground">
                      {fullName}
                    </p>
                    <p className="text-xs text-primary font-medium">
                      {member.position_title || member.position}
                    </p>
                    {member.department && (
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        {member.department}
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </section>
    </div>
  )
}

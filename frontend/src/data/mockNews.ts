/**
 * Mock content layer for the Eagle Eye public site.
 *
 * The backend does not yet expose a News/Articles API (only the generic
 * FastAPI template's Users/Items endpoints exist). Until `NewsService` /
 * `CategoriesService` land in `src/client`, every public page reads from
 * this module instead.
 *
 * The shapes below intentionally mirror what a REST article resource will
 * likely look like (slug-based routing, ISO timestamps, author sub-object,
 * category enum) so that swapping this file for real `@tanstack/react-query`
 * calls later is mostly a drop-in replacement. Search for "TODO(api)" for the
 * exact spots to wire up.
 */

export interface Author {
  id: string
  name: string
  role: string
  avatarUrl?: string
}

export interface Category {
  slug: string
  name: string
  description: string
}

export interface Article {
  id: string
  slug: string
  title: string
  excerpt: string
  content: string[]
  category: Category["slug"]
  author: Author
  publishedAt: string
  updatedAt?: string
  readTimeMinutes: number
  coverImageUrl: string
  coverImageAlt: string
  featured?: boolean
  tags: string[]
}

export const categories: Category[] = [
  {
    slug: "school-news",
    name: "School News",
    description: "Announcements, events, and happenings around CDLB campus.",
  },
  {
    slug: "academics",
    name: "Academics",
    description: "Classroom milestones, honors, and academic competitions.",
  },
  {
    slug: "sports",
    name: "Sports",
    description: "Game recaps, athlete spotlights, and team standings.",
  },
  {
    slug: "arts-culture",
    name: "Arts & Culture",
    description: "Performances, exhibits, and creative student work.",
  },
  {
    slug: "opinion",
    name: "Opinion",
    description: "Student voices and editorials on issues that matter.",
  },
  {
    slug: "features",
    name: "Features",
    description: "Long-form stories about students, staff, and campus life.",
  },
]

const authors: Record<string, Author> = {
  mari: { id: "a1", name: "Mari Santos", role: "Editor-in-Chief" },
  jc: { id: "a2", name: "JC Dela Peña", role: "Sports Editor" },
  ren: { id: "a3", name: "Ren Bautista", role: "Staff Writer" },
  alex: { id: "a4", name: "Alex Villanueva", role: "Arts Correspondent" },
  sam: { id: "a5", name: "Sam Ocampo", role: "Opinion Columnist" },
  kit: { id: "a6", name: "Kit Fernandez", role: "News Reporter" },
}

const placeholderImage = (seed: string, w = 1200, h = 700) =>
  `https://picsum.photos/seed/${seed}/${w}/${h}`

export const articles: Article[] = [
  {
    id: "1",
    slug: "cdlb-wins-regional-press-conference",
    title:
      "CDLB Media Club Sweeps Regional Schools Press Conference for Third Year Running",
    excerpt:
      "Eagle Eye staffers brought home eleven medals, including three golds in editorial writing and news writing, cementing the club's reputation as one of the region's strongest school papers.",
    content: [
      "The CDLB Media Club once again proved its dominance at this year's Regional Schools Press Conference, taking home eleven medals across news writing, editorial writing, photojournalism, and layout design.",
      'Editor-in-Chief Mari Santos led the delegation, which spent three days competing against forty other schools in the division. "Every writer on this team put in months of practice," Santos said. "This is a testament to their discipline, not luck."',
      "Standouts included gold medals in editorial writing and news writing, along with a strong showing in the photojournalism category, where staff photographers captured candid campus moments that judges praised for their storytelling.",
      'The club\'s moderator, Mr. Reyes, credited the win to consistent weekly workshops held throughout the school year. "We treat every issue of Eagle Eye like a competition piece," he said. "That habit shows when the judges are watching."',
      "With the regional win secured, the team now turns its attention to the provincial meet next month, where they hope to qualify for nationals for the second consecutive year.",
    ],
    category: "school-news",
    author: authors.mari,
    publishedAt: "2026-08-28T09:00:00+08:00",
    readTimeMinutes: 4,
    coverImageUrl: placeholderImage("press-conference"),
    coverImageAlt:
      "Student journalists holding medals on stage at a press conference awarding ceremony",
    featured: true,
    tags: ["media club", "competition", "awards"],
  },
  {
    id: "2",
    slug: "new-stem-laboratory-opens",
    title: "New STEM Laboratory Opens Its Doors to Senior High Students",
    excerpt:
      "The long-awaited science laboratory finally opened this week, giving STEM strand students hands-on access to equipment previously available only through university partnerships.",
    content: [
      "After nearly a year of construction, CDLB's new STEM laboratory officially opened its doors to senior high school students this week.",
      "The facility includes dedicated stations for physics, chemistry, and biology experiments, along with a small computer lab for data analysis and simulations.",
      '"We used to travel off-campus just to run basic experiments," said one Grade 12 STEM student. "Now everything we need is a few steps from our classroom."',
      "School administrators say the lab was funded through a combination of alumni donations and a local government grant, and that a second phase — adding a robotics corner — is already being planned for next year.",
    ],
    category: "academics",
    author: authors.kit,
    publishedAt: "2026-08-25T13:30:00+08:00",
    readTimeMinutes: 3,
    coverImageUrl: placeholderImage("stem-lab"),
    coverImageAlt:
      "Students in lab coats working at a science laboratory bench",
    featured: true,
    tags: ["STEM", "facilities", "senior high"],
  },
  {
    id: "3",
    slug: "eagles-basketball-clinches-division-finals",
    title:
      "Eagles Basketball Clinches Spot in Division Finals After Buzzer-Beater",
    excerpt:
      "A last-second three-pointer sent the home crowd into a frenzy as the CDLB Eagles edged out their long-time rivals to advance to the division finals.",
    content: [
      "The gymnasium erupted as senior guard Miggy Torres sank a buzzer-beating three-pointer, sending the CDLB Eagles to the division finals with a 58-56 win over their cross-town rivals.",
      "The game had been tied for most of the fourth quarter, with both teams trading leads down the stretch. Coach Dizon called a timeout with 12 seconds left to draw up the final play.",
      '"We practiced that exact inbound play all week," Torres said after the game. "I just had to trust it would be open."',
      "The Eagles will face the defending champions in the finals next Saturday, a rematch of last year's heartbreaking loss in overtime.",
    ],
    category: "sports",
    author: authors.jc,
    publishedAt: "2026-08-24T19:45:00+08:00",
    readTimeMinutes: 3,
    coverImageUrl: placeholderImage("basketball-finals"),
    coverImageAlt: "Basketball player shooting a three-pointer during a game",
    featured: true,
    tags: ["basketball", "varsity", "division finals"],
  },
  {
    id: "4",
    slug: "student-art-exhibit-campus-gallery",
    title: '"Fragments": Student Art Exhibit Turns Hallway Into Gallery',
    excerpt:
      "Twenty student artists transformed the second-floor hallway into a temporary gallery, exploring themes of identity and memory through mixed media.",
    content: [
      'For one week, the usually quiet second-floor hallway of the main building became a full gallery space, hosting "Fragments," a mixed-media exhibit by twenty student artists.',
      "The exhibit, organized by the Fine Arts Club, explored themes of identity, memory, and belonging through painting, collage, and found-object sculpture.",
      '"A lot of these pieces started as journal entries," said exhibit curator and Grade 11 student Nica Ramos. "We wanted people to walk through and feel like they were reading someone\'s diary."',
      "Faculty and students who visited during lunch breaks described the exhibit as a rare, welcome change of pace in the middle of a hectic school week.",
    ],
    category: "arts-culture",
    author: authors.alex,
    publishedAt: "2026-08-22T11:15:00+08:00",
    readTimeMinutes: 3,
    coverImageUrl: placeholderImage("art-exhibit"),
    coverImageAlt:
      "Colorful mixed-media artwork displayed along a school hallway",
    tags: ["fine arts", "exhibit", "student life"],
  },
  {
    id: "5",
    slug: "opinion-grading-period-length",
    title: "Opinion: It's Time to Rethink How Long Our Grading Periods Are",
    excerpt:
      "Cramming a full unit of content into six weeks leaves little room to actually absorb material. Maybe the answer isn't more homework — it's a longer runway.",
    content: [
      "Every grading period, the same pattern repeats: a slow start, a frantic middle, and a chaotic final week of quizzes stacked on top of quizzes.",
      "It's easy to blame students for poor time management, but six-week grading periods leave very little room for both depth and rest. Teachers are rushing to finish content; students are rushing to keep up.",
      "A shift to eight- or nine-week periods, paired with a lighter courseload per quarter, could give both groups room to breathe without sacrificing rigor.",
      "This isn't a call to lower standards. It's a call to give the standards we already have a fair chance to be met.",
    ],
    category: "opinion",
    author: authors.sam,
    publishedAt: "2026-08-20T08:00:00+08:00",
    readTimeMinutes: 4,
    coverImageUrl: placeholderImage("opinion-grading"),
    coverImageAlt: "Empty classroom desks arranged in rows",
    tags: ["editorial", "academics", "student voice"],
  },
  {
    id: "6",
    slug: "profile-janitor-40-years",
    title: "Forty Years on Campus: A Conversation With Mang Tonio",
    excerpt:
      "He's outlasted six principals and thousands of students. Mang Tonio, CDLB's longest-serving maintenance staff, reflects on four decades of quietly keeping the school running.",
    content: [
      "Ask any alumnus from the last four decades who Mang Tonio is, and most will smile before answering. He's swept the same hallways, fixed the same leaky faucets, and greeted the same nervous incoming freshmen since 1986.",
      '"I\'ve seen this school through six principals," he says, chuckling. "The uniforms changed, the buildings changed. The students, though — they\'re still the same kind of restless every August."',
      "Mang Tonio says his favorite part of the job has never been the routine — it's the small conversations. Students stopping to ask how his day is going, or slipping him a snack during exam week.",
      "As CDLB celebrates its anniversary this year, staff and students alike agree: no history of the school is complete without him in it.",
    ],
    category: "features",
    author: authors.ren,
    publishedAt: "2026-08-18T10:00:00+08:00",
    readTimeMinutes: 5,
    coverImageUrl: placeholderImage("profile-staff"),
    coverImageAlt:
      "An elderly maintenance staff member sweeping a school hallway",
    tags: ["profile", "school history", "staff"],
  },
  {
    id: "7",
    slug: "debate-team-qualifies-nationals",
    title: "Debate Team Qualifies for Nationals After Undefeated Run",
    excerpt:
      "CDLB's varsity debate team went undefeated through the provincial elimination rounds, punching their ticket to the national championships in October.",
    content: [
      "CDLB's varsity debate team secured a spot at this year's national championships after an undefeated run through the provincial elimination rounds.",
      "The team, composed of four senior debaters, won all six of their preliminary rounds before sweeping the semifinal and final matches on points.",
      '"We spent our summer doing mock debates almost every weekend," said team captain Bea Lorenzo. "It\'s surreal that it\'s actually paying off."',
      "The national championships will be held in October, where the team will face off against the country's top-ranked debate programs.",
    ],
    category: "school-news",
    author: authors.kit,
    publishedAt: "2026-08-15T14:20:00+08:00",
    readTimeMinutes: 3,
    coverImageUrl: placeholderImage("debate-team"),
    coverImageAlt: "Students standing at podiums during a debate competition",
    tags: ["debate", "competition", "nationals"],
  },
  {
    id: "8",
    slug: "volleyball-team-fundraiser",
    title: "Girls' Volleyball Team Hosts Bake Sale to Fund Nationals Trip",
    excerpt:
      "With official school funding covering only part of the trip, the volleyball team turned to a weeklong bake sale to close the gap ahead of nationals.",
    content: [
      "The girls' volleyball team spent the week running a campus-wide bake sale to help cover travel costs for their upcoming national tournament appearance.",
      "Team members took turns baking and selling everything from brownies to ube cupcakes during recess and lunch periods, with parents also pitching in with donated goods.",
      '"The school covers a portion of the trip, but hotel and transportation for a team this size adds up fast," said team manager Trisha Aquino.',
      "By the end of the week, the team had raised enough to cover nearly half of the remaining balance, with a second fundraiser already being planned.",
    ],
    category: "sports",
    author: authors.jc,
    publishedAt: "2026-08-12T09:30:00+08:00",
    readTimeMinutes: 2,
    coverImageUrl: placeholderImage("volleyball-bakesale"),
    coverImageAlt: "Students at a table selling baked goods on campus",
    tags: ["volleyball", "fundraiser", "nationals"],
  },
  {
    id: "9",
    slug: "choir-wins-national-folk-song-competition",
    title: "CDLB Chorale Takes Gold at National Folk Song Competition",
    excerpt:
      "Months of after-school rehearsals paid off as the CDLB Chorale bested nineteen other choirs to win gold in the folk song category.",
    content: [
      "The CDLB Chorale brought home the gold medal in the folk song category at this year's National Choral Competition, beating out nineteen other participating schools.",
      "The choir's arrangement of a traditional Visayan folk song was singled out by judges for its dynamic range and tight harmonies.",
      '"We rehearsed almost every day after classes for two months," said choir president Denise Lim. "Standing on that stage, all of it just clicked."',
      "Choir moderator Ms. Villaflor said this is the group's strongest placement in over a decade, and the chorale plans to perform the winning piece at the school's upcoming anniversary program.",
    ],
    category: "arts-culture",
    author: authors.alex,
    publishedAt: "2026-08-09T16:00:00+08:00",
    readTimeMinutes: 3,
    coverImageUrl: placeholderImage("chorale-gold"),
    coverImageAlt: "A school choir performing on stage in matching outfits",
    tags: ["chorale", "competition", "music"],
  },
  {
    id: "10",
    slug: "opinion-club-fair-overcrowding",
    title:
      "Opinion: The Club Fair Needs a Better System Than First-Come, First-Served",
    excerpt:
      "Popular clubs fill up in minutes while others struggle to hit quota — and students who arrive late or have back-to-back classes are the ones who lose out.",
    content: [
      "Every year, the same clubs fill their rosters within the first fifteen minutes of the club fair, while students with back-to-back classes miss out entirely.",
      "A staggered sign-up window — by year level, or even just by last name — would spread out demand without requiring a total overhaul of the event.",
      "It's a small logistical fix, but one that would make club recruitment feel less like a race and more like an actual choice.",
    ],
    category: "opinion",
    author: authors.sam,
    publishedAt: "2026-08-05T08:00:00+08:00",
    readTimeMinutes: 2,
    coverImageUrl: placeholderImage("club-fair"),
    coverImageAlt: "Students gathered around booths at a school club fair",
    tags: ["editorial", "student life", "clubs"],
  },
  {
    id: "11",
    slug: "grade-10-robotics-regional-award",
    title:
      "Grade 10 Robotics Team Places Second in Regional Robotics Challenge",
    excerpt:
      "In their first year competing, the newly formed robotics team surprised organizers with a second-place finish in the obstacle course category.",
    content: [
      "In just their first year of competing, CDLB's Grade 10 robotics team placed second in the obstacle course category at the Regional Robotics Challenge.",
      "The four-member team spent weekends building and reprogramming their robot after school hours, often troubleshooting late into the evening ahead of competition day.",
      '"We didn\'t expect to place at all, honestly," said team member Josh Tan. "Second place as rookies feels unreal."',
      "The team says they're already planning upgrades to their robot's sensor array ahead of next year's competition.",
    ],
    category: "academics",
    author: authors.kit,
    publishedAt: "2026-08-02T12:00:00+08:00",
    readTimeMinutes: 3,
    coverImageUrl: placeholderImage("robotics-team"),
    coverImageAlt: "Students working on a small robot at a competition table",
    tags: ["robotics", "STEM", "competition"],
  },
  {
    id: "12",
    slug: "alumni-homecoming-2026",
    title: "Alumni Homecoming Draws Record Turnout for CDLB's Anniversary Year",
    excerpt:
      "Graduates spanning five decades returned to campus for a weekend of reunions, campus tours, and a much-anticipated alumni-varsity basketball game.",
    content: [
      "CDLB welcomed its largest alumni homecoming turnout in recent memory this past weekend, part of a series of events marking the school's anniversary year.",
      "Graduates from as far back as the 1980s toured renovated campus buildings, many remarking on how unrecognizable — and how familiar — the school felt at once.",
      "The weekend closed with an alumni-versus-varsity basketball exhibition game, which the current varsity team narrowly won in overtime.",
      '"It\'s strange seeing your old classroom turned into a computer lab," said one attendee from the class of 1994. "But walking through that gate still feels exactly the same."',
    ],
    category: "features",
    author: authors.ren,
    publishedAt: "2026-07-30T10:00:00+08:00",
    readTimeMinutes: 4,
    coverImageUrl: placeholderImage("homecoming"),
    coverImageAlt:
      "Adults and students gathered on a school campus for a reunion event",
    tags: ["alumni", "anniversary", "campus life"],
  },
]

// ---------------------------------------------------------------------------
// Query helpers
//
// TODO(api): Replace these with real network calls once the backend exposes
// article endpoints, e.g.:
//   NewsService.readArticles({ query: { category, page, pageSize } })
//   NewsService.readArticleBySlug({ path: { slug } })
// The function signatures below are written so call sites won't need to
// change shape when that happens — only the implementation swaps out.
// ---------------------------------------------------------------------------

export interface ArticleListParams {
  category?: string
  page?: number
  pageSize?: number
  query?: string
}

export interface ArticleListResult {
  items: Article[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

const sortedByDate = [...articles].sort(
  (a, b) =>
    new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime(),
)

export function getFeaturedArticles(limit = 3): Article[] {
  return sortedByDate.filter((a) => a.featured).slice(0, limit)
}

export function getLatestArticles(limit = 6): Article[] {
  return sortedByDate.slice(0, limit)
}

export function getArticlesByCategory(
  categorySlug: string,
  limit?: number,
): Article[] {
  const list = sortedByDate.filter((a) => a.category === categorySlug)
  return typeof limit === "number" ? list.slice(0, limit) : list
}

export function getArticleList(
  params: ArticleListParams = {},
): ArticleListResult {
  const { category, page = 1, pageSize = 6, query } = params

  let filtered = sortedByDate
  if (category) {
    filtered = filtered.filter((a) => a.category === category)
  }
  if (query) {
    filtered = searchArticlesList(query, filtered)
  }

  const total = filtered.length
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const safePage = Math.min(Math.max(1, page), totalPages)
  const start = (safePage - 1) * pageSize

  return {
    items: filtered.slice(start, start + pageSize),
    total,
    page: safePage,
    pageSize,
    totalPages,
  }
}

export function getArticleBySlug(slug: string): Article | undefined {
  return articles.find((a) => a.slug === slug)
}

export function getRelatedArticles(article: Article, limit = 3): Article[] {
  return sortedByDate
    .filter((a) => a.id !== article.id && a.category === article.category)
    .slice(0, limit)
}

export function getCategoryBySlug(slug: string): Category | undefined {
  return categories.find((c) => c.slug === slug)
}

function searchArticlesList(
  query: string,
  source: Article[] = articles,
): Article[] {
  const q = query.trim().toLowerCase()
  if (!q) return []
  return source.filter((a) => {
    const haystack = [
      a.title,
      a.excerpt,
      a.content.join(" "),
      a.author.name,
      getCategoryBySlug(a.category)?.name ?? "",
      ...a.tags,
    ]
      .join(" ")
      .toLowerCase()
    return haystack.includes(q)
  })
}

export function searchArticles(
  query: string,
  params: { page?: number; pageSize?: number } = {},
): ArticleListResult {
  const { page = 1, pageSize = 6 } = params
  const filtered = searchArticlesList(query)
  const total = filtered.length
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const safePage = Math.min(Math.max(1, page), totalPages)
  const start = (safePage - 1) * pageSize

  return {
    items: filtered.slice(start, start + pageSize),
    total,
    page: safePage,
    pageSize,
    totalPages,
  }
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

export function formatShortDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  })
}

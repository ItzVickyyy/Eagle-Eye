import { apiRequest } from "./userFactory"

export interface Category {
  id: number
  name: string
  slug: string
  description?: string | null
}

/** Public categories list (no auth required). */
export async function getCategories(): Promise<Category[]> {
  const data = await apiRequest("/api/v1/categories/")
  const rows: Category[] = data?.data ?? []
  if (rows.length === 0) {
    throw new Error("No categories available to seed content against")
  }
  return rows
}

export async function pickCategorySlug(slug: string): Promise<Category> {
  const rows = await getCategories()
  const match = rows.find((c) => c.slug === slug)
  if (!match) throw new Error(`Category with slug "${slug}" not found`)
  return match
}

export interface NewArticle {
  token: string
  headline: string
  slug?: string
  body?: string
  excerpt?: string
  coverImageUrl?: string
  categoryId?: number
  status?: "draft" | "pending" | "published" | "archived"
}

export interface ArticleRecord {
  id: string
  slug: string
  headline: string
  status: string
  author_id?: string | null
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "")
}

export async function apiCreateArticle(a: NewArticle): Promise<ArticleRecord> {
  const data = await apiRequest(
    "/api/v1/articles/",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        headline: a.headline,
        slug: a.slug ?? slugify(a.headline),
        excerpt: a.excerpt,
        cover_image_url: a.coverImageUrl,
        body: a.body ?? "<p>Body text.</p>",
        category_id: a.categoryId,
        status: a.status ?? "draft",
        tag_ids: [],
      }),
    },
    a.token,
  )
  return {
    id: data.id,
    slug: data.slug,
    headline: data.headline,
    status: data.status,
    author_id: data.author_id,
  }
}

export async function submitContactMessage(payload: {
  name: string
  email: string
  subject: string
  message: string
}): Promise<void> {
  await apiRequest("/api/v1/contact/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
}

export async function postComment(payload: {
  articleId: string
  guestName: string
  guestEmail: string
  body: string
}): Promise<void> {
  await apiRequest("/api/v1/comments/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      article_id: payload.articleId,
      guest_name: payload.guestName,
      guest_email: payload.guestEmail,
      body: payload.body,
    }),
  })
}

export async function getArticleCommentsPublic(
  articleId: string,
): Promise<any[]> {
  const data = await apiRequest(`/api/v1/comments/article/${articleId}`)
  return data?.data ?? []
}

export async function getContactMessages(token: string): Promise<any[]> {
  const data = await apiRequest("/api/v1/contact/", {}, token)
  return data?.data ?? []
}

export async function markContactMessageRead(
  token: string,
  id: string,
): Promise<void> {
  await apiRequest(
    `/api/v1/contact/${id}/mark-read`,
    { method: "PATCH" },
    token,
  )
}

export async function createClubMember(
  token: string,
  member: {
    first_name: string
    last_name: string
    position_title?: string
    department?: string
    photo_url?: string
    is_officer?: boolean
    is_active?: boolean
  },
): Promise<{ id: string }> {
  const data = await apiRequest(
    "/api/v1/club-members/",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(member),
    },
    token,
  )
  return { id: data.id }
}

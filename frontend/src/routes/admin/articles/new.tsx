import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import {
  ArrowLeft,
  CheckCircle,
  Eye,
  Image as ImageIcon,
  Save,
  Send,
  Upload,
} from "lucide-react"
import { useEffect, useState } from "react"
import { z } from "zod"

import {
  type ArticleStatus,
  ArticlesService,
  CategoriesService,
  MediaService,
  TagsService,
} from "@/client"
import { RichTextEditor } from "@/components/Admin/RichTextEditor"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { sanitizeHtml } from "@/lib/sanitize"

const searchSchema = z.object({
  editId: z.string().optional().catch(undefined),
})

export const Route = createFileRoute("/admin/articles/new")({
  component: NewArticle,
  validateSearch: searchSchema,
  head: () => ({
    meta: [{ title: "Write Article — Eagle Eye" }],
  }),
})

function NewArticle() {
  const { editId } = Route.useSearch()
  const navigate = useNavigate()
  const { user: currentUser } = useAuth()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const isStaffAdmin =
    currentUser?.is_superuser ||
    currentUser?.role === "super_admin" ||
    currentUser?.role === "admin"

  const [headline, setHeadline] = useState("")
  const [excerpt, setExcerpt] = useState("")
  const [body, setBody] = useState("")
  const [categoryId, setCategoryId] = useState<number | undefined>(undefined)
  const [tagsInput, setTagsInput] = useState("")
  const [coverImageUrl, setCoverImageUrl] = useState("")
  const [uploadingImage, setUploadingImage] = useState(false)
  const [activeTab, setActiveTab] = useState("write")

  // Fetch categories
  const { data: categoriesRes } = useQuery({
    queryKey: ["admin-categories"],
    queryFn: () => CategoriesService.readCategories({ query: { limit: 100 } }),
  })

  const categories: any[] =
    (categoriesRes?.data as any)?.data || (categoriesRes as any)?.data || []

  // Fetch tags
  const { data: tagsRes } = useQuery({
    queryKey: ["admin-tags"],
    queryFn: () => TagsService.readTags({ query: { limit: 100 } }),
  })

  const availableTags: any[] =
    (tagsRes?.data as any)?.data || (tagsRes as any)?.data || []

  // If editing, fetch article
  const { data: existingArticleRes } = useQuery({
    queryKey: ["article-edit", editId],
    queryFn: () =>
      editId
        ? ArticlesService.getArticleById({ path: { id: String(editId) } })
        : Promise.resolve(null),
    enabled: !!editId,
  })

  useEffect(() => {
    if (existingArticleRes) {
      const article: any =
        (existingArticleRes as any)?.data || existingArticleRes
      setHeadline(article.headline || "")
      setExcerpt(article.excerpt || "")
      setBody(article.body || "")
      setCategoryId(article.category_id || undefined)
      setCoverImageUrl(article.cover_image_url || "")
      if (article.tags && Array.isArray(article.tags)) {
        setTagsInput(article.tags.map((t: any) => t.name).join(", "))
      } else {
        setTagsInput("")
      }
    }
  }, [existingArticleRes])

  // Save / Update mutation
  const saveMutation = useMutation({
    mutationFn: async (targetStatus: ArticleStatus) => {
      const slug = headline
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/(^-|-$)/g, "")

      const rawTagNames = tagsInput
        .split(",")
        .map((t) => t.trim().replace(/^#/, ""))
        .filter(Boolean)

      const tagIds: number[] = []
      for (const name of rawTagNames) {
        const found = availableTags.find(
          (t: any) => t.name.toLowerCase() === name.toLowerCase(),
        )
        if (found) {
          tagIds.push(found.id)
        } else {
          try {
            const res: any = await TagsService.createTag({
              body: { name },
            })
            const createdTag = res?.data || res
            if (createdTag?.id) {
              tagIds.push(createdTag.id)
            }
          } catch {
            // ignore
          }
        }
      }
      const uniqueTagIds = Array.from(new Set(tagIds))

      if (editId) {
        return await ArticlesService.updateArticle({
          path: { id: String(editId) },
          body: {
            headline: headline.trim(),
            slug: slug || undefined,
            excerpt: excerpt.trim() || undefined,
            body: body.trim(),
            category_id: categoryId,
            cover_image_url: coverImageUrl.trim() || undefined,
            status: targetStatus,
            tag_ids: uniqueTagIds,
          },
        })
      }
      return await ArticlesService.createArticle({
        body: {
          headline: headline.trim(),
          slug: slug || "untitled",
          excerpt: excerpt.trim() || undefined,
          body: body.trim(),
          category_id: categoryId,
          cover_image_url: coverImageUrl.trim() || undefined,
          status: targetStatus,
          tag_ids: uniqueTagIds,
        },
      })
    },
    onSuccess: (_, status) => {
      const label =
        status === "published"
          ? "published"
          : status === "pending"
            ? "submitted for review"
            : "saved as draft"
      showSuccessToast(`Article successfully ${label}!`)
      queryClient.invalidateQueries({ queryKey: ["admin-articles"] })
      queryClient.invalidateQueries({ queryKey: ["review-queue"] })
      navigate({ to: "/admin/articles" })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to save article")
    },
  })

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploadingImage(true)
    try {
      const res: any = await MediaService.uploadFile({
        body: { file },
      })
      const uploadedUrl = res?.data?.file_url || res?.file_url
      if (uploadedUrl) {
        setCoverImageUrl(uploadedUrl)
        showSuccessToast("Cover image uploaded!")
      }
    } catch (err: any) {
      showErrorToast(err.message || "Failed to upload file")
    } finally {
      setUploadingImage(false)
    }
  }

  const isBodyEmpty = (content: string) => {
    const trimmed = content.trim()
    if (!trimmed) return true
    const stripped = trimmed
      .replace(/<p><\/p>/gi, "")
      .replace(/<p><br\s*\/?><\/p>/gi, "")
      .replace(/<br\s*\/?>/gi, "")
      .replace(/&nbsp;/gi, " ")
      .trim()
    return stripped.length === 0 && !trimmed.includes("<img")
  }

  const handleSave = (status: ArticleStatus) => {
    if (!headline.trim()) {
      showErrorToast("Please enter an article headline")
      return
    }
    if (isBodyEmpty(body)) {
      showErrorToast("Please enter article content")
      return
    }
    saveMutation.mutate(status)
  }

  return (
    <div className="flex flex-col gap-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" size="icon">
            <Link to="/admin/articles">
              <ArrowLeft className="size-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              {editId ? "Edit Article" : "Write Article"}
            </h1>
            <p className="text-muted-foreground text-sm">
              {editId
                ? "Update story details and publication state."
                : "Draft a new story for the Eagle Eye newsroom."}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <LoadingButton
            variant="outline"
            size="sm"
            loading={saveMutation.isPending}
            onClick={() => handleSave("draft")}
            className="gap-1.5"
          >
            <Save className="size-4" />
            Save Draft
          </LoadingButton>

          <LoadingButton
            variant="secondary"
            size="sm"
            loading={saveMutation.isPending}
            onClick={() => handleSave("pending")}
            className="gap-1.5"
          >
            <Send className="size-4 text-amber-500" />
            Submit for Review
          </LoadingButton>

          {isStaffAdmin && (
            <LoadingButton
              variant="default"
              size="sm"
              loading={saveMutation.isPending}
              onClick={() => handleSave("published")}
              className="gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              <CheckCircle className="size-4" />
              Publish
            </LoadingButton>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Main Content Area */}
        <div className="md:col-span-2 flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <Label htmlFor="headline" className="font-semibold">
              Headline <span className="text-destructive">*</span>
            </Label>
            <Input
              id="headline"
              placeholder="e.g. CDLB Launches Campus-Wide Journalism Workshop"
              value={headline}
              onChange={(e) => setHeadline(e.target.value)}
              className="font-serif text-lg font-bold"
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="excerpt" className="font-semibold">
              Excerpt / Subtitle
            </Label>
            <Textarea
              id="excerpt"
              placeholder="A brief 1-2 sentence summary of the article..."
              rows={2}
              value={excerpt}
              onChange={(e) => setExcerpt(e.target.value)}
            />
          </div>

          <Tabs
            value={activeTab}
            onValueChange={setActiveTab}
            className="w-full"
          >
            <div className="flex items-center justify-between pb-2">
              <Label className="font-semibold">
                Story Content <span className="text-destructive">*</span>
              </Label>
              <TabsList className="h-8">
                <TabsTrigger value="write" className="text-xs">
                  Write
                </TabsTrigger>
                <TabsTrigger value="preview" className="text-xs gap-1">
                  <Eye className="size-3" /> Preview
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="write" className="m-0">
              <RichTextEditor
                value={body}
                onChange={setBody}
                placeholder="Write your article body here... Add headings, quotes, lists, links, images, and rich formatting."
                disabled={saveMutation.isPending}
              />
            </TabsContent>

            <TabsContent value="preview" className="m-0">
              <div className="min-h-[380px] rounded-md border bg-card p-6">
                <div
                  className="prose-content space-y-4 text-base leading-relaxed text-foreground"
                  dangerouslySetInnerHTML={{
                    __html:
                      sanitizeHtml(body.trim()) ||
                      "<p class='text-muted-foreground italic'>Nothing to preview yet.</p>",
                  }}
                />
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* Sidebar Metadata */}
        <div className="flex flex-col gap-5">
          <div className="rounded-xl border bg-card p-5 flex flex-col gap-4">
            <h3 className="font-semibold text-sm">Article Settings</h3>

            <div className="flex flex-col gap-2">
              <Label htmlFor="category" className="text-xs font-medium">
                Category
              </Label>
              <Select
                value={categoryId ? String(categoryId) : undefined}
                onValueChange={(val) => setCategoryId(Number(val))}
              >
                <SelectTrigger id="category" className="w-full">
                  <SelectValue placeholder="Select a category" />
                </SelectTrigger>
                <SelectContent>
                  {categories.map((c) => (
                    <SelectItem key={c.id} value={String(c.id)}>
                      {c.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="tags" className="text-xs font-medium">
                Tags (comma separated)
              </Label>
              <Input
                id="tags"
                placeholder="news, sports, workshop"
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
              />
              {tagsInput && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {tagsInput
                    .split(",")
                    .map((t) => t.trim().replace(/^#/, ""))
                    .filter(Boolean)
                    .map((tag) => (
                      <Badge
                        key={tag}
                        variant="secondary"
                        className="text-[10px]"
                      >
                        #{tag}
                      </Badge>
                    ))}
                </div>
              )}
              {availableTags.length > 0 && (
                <div className="flex flex-col gap-1 mt-1">
                  <span className="text-[11px] text-muted-foreground">
                    Available tags (click to add):
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {availableTags.map((t: any) => (
                      <Badge
                        key={t.id}
                        variant="outline"
                        className="cursor-pointer text-[10px] hover:bg-secondary transition-colors"
                        onClick={() => {
                          const current = tagsInput
                            .split(",")
                            .map((tag) => tag.trim().replace(/^#/, ""))
                            .filter(Boolean)
                          if (
                            !current.some(
                              (tag) =>
                                tag.toLowerCase() === t.name.toLowerCase(),
                            )
                          ) {
                            const updated = [...current, t.name].join(", ")
                            setTagsInput(updated)
                          }
                        }}
                      >
                        +{t.name}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Cover Image Card */}
          <div className="rounded-xl border bg-card p-5 flex flex-col gap-4">
            <h3 className="font-semibold text-sm">Cover Image</h3>

            {coverImageUrl ? (
              <div className="relative aspect-video w-full rounded-md overflow-hidden border bg-muted">
                <img
                  src={coverImageUrl}
                  alt="Cover preview"
                  className="size-full object-cover"
                />
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setCoverImageUrl("")}
                  className="absolute bottom-2 right-2 text-xs h-7"
                >
                  Remove
                </Button>
              </div>
            ) : (
              <div className="border border-dashed rounded-lg p-6 flex flex-col items-center justify-center text-center bg-muted/20">
                <ImageIcon className="size-8 text-muted-foreground/60 mb-2" />
                <p className="text-xs text-muted-foreground mb-3">
                  Upload an image or paste a direct URL below
                </p>
                <label className="cursor-pointer">
                  <span className="inline-flex items-center gap-1.5 rounded-md bg-secondary px-3 py-1.5 text-xs font-medium text-secondary-foreground hover:bg-secondary/80">
                    <Upload className="size-3.5" />
                    {uploadingImage ? "Uploading..." : "Upload Image"}
                  </span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleFileUpload}
                    disabled={uploadingImage}
                    className="sr-only"
                  />
                </label>
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <Label
                htmlFor="imageUrl"
                className="text-[11px] text-muted-foreground"
              >
                Or direct image URL
              </Label>
              <Input
                id="imageUrl"
                placeholder="https://..."
                value={coverImageUrl}
                onChange={(e) => setCoverImageUrl(e.target.value)}
                className="text-xs h-8"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

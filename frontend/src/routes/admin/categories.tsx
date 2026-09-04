import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import {
  Edit,
  FolderTree,
  PlusCircle,
  Tag as TagIcon,
  Trash2,
  X,
} from "lucide-react"
import { useState } from "react"

import { CategoriesService, TagsService, UsersService } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/admin/categories")({
  component: Categories,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    const isStaffAdmin =
      user.is_superuser || user.role === "super_admin" || user.role === "admin"
    if (!isStaffAdmin) {
      throw redirect({
        to: "/admin",
      })
    }
  },
  head: () => ({
    meta: [{ title: "Categories & Tags — Eagle Eye" }],
  }),
})

function Categories() {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  // Category state
  const [categoryModalOpen, setCategoryModalOpen] = useState(false)
  const [editingCategory, setEditingCategory] = useState<any | null>(null)
  const [categoryName, setCategoryName] = useState("")
  const [categoryDesc, setCategoryDesc] = useState("")
  const [categoryToDelete, setCategoryToDelete] = useState<any | null>(null)

  // Tag state
  const [newTagName, setNewTagName] = useState("")

  // Queries
  const { data: categoriesRes, isLoading: loadingCategories } = useQuery({
    queryKey: ["admin-categories"],
    queryFn: () => CategoriesService.readCategories({ query: { limit: 100 } }),
  })

  const { data: tagsRes, isLoading: loadingTags } = useQuery({
    queryKey: ["admin-tags"],
    queryFn: () => TagsService.readTags({ query: { limit: 100 } }),
  })

  const categories: any[] =
    (categoriesRes?.data as any)?.data || (categoriesRes as any)?.data || []
  const tags: any[] =
    (tagsRes?.data as any)?.data || (tagsRes as any)?.data || []

  // Category Mutations
  const createCategoryMutation = useMutation({
    mutationFn: () => {
      const slug = categoryName
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/(^-|-$)/g, "")
      return CategoriesService.createCategory({
        body: {
          name: categoryName.trim(),
          slug: slug || "category",
          description: categoryDesc.trim() || undefined,
        },
      })
    },
    onSuccess: () => {
      showSuccessToast("Category created successfully")
      setCategoryModalOpen(false)
      setCategoryName("")
      setCategoryDesc("")
      queryClient.invalidateQueries({ queryKey: ["admin-categories"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to create category")
    },
  })

  const updateCategoryMutation = useMutation({
    mutationFn: () =>
      CategoriesService.updateCategory({
        path: { id: editingCategory.id },
        body: {
          name: categoryName.trim(),
          description: categoryDesc.trim() || undefined,
        },
      }),
    onSuccess: () => {
      showSuccessToast("Category updated successfully")
      setCategoryModalOpen(false)
      setEditingCategory(null)
      setCategoryName("")
      setCategoryDesc("")
      queryClient.invalidateQueries({ queryKey: ["admin-categories"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to update category")
    },
  })

  const deleteCategoryMutation = useMutation({
    mutationFn: (id: number) =>
      CategoriesService.deleteCategory({ path: { id } }),
    onSuccess: () => {
      showSuccessToast("Category deleted successfully")
      setCategoryToDelete(null)
      queryClient.invalidateQueries({ queryKey: ["admin-categories"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to delete category")
    },
  })

  // Tag Mutations
  const createTagMutation = useMutation({
    mutationFn: (name: string) =>
      TagsService.createTag({
        body: { name: name.trim().replace(/^#/, "") },
      }),
    onSuccess: () => {
      showSuccessToast("Tag created successfully")
      setNewTagName("")
      queryClient.invalidateQueries({ queryKey: ["admin-tags"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to create tag")
    },
  })

  const deleteTagMutation = useMutation({
    mutationFn: (id: number) => TagsService.deleteTag({ path: { id } }),
    onSuccess: () => {
      showSuccessToast("Tag removed")
      queryClient.invalidateQueries({ queryKey: ["admin-tags"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to delete tag")
    },
  })

  const openCreateCategory = () => {
    setEditingCategory(null)
    setCategoryName("")
    setCategoryDesc("")
    setCategoryModalOpen(true)
  }

  const openEditCategory = (cat: any) => {
    setEditingCategory(cat)
    setCategoryName(cat.name)
    setCategoryDesc(cat.description || "")
    setCategoryModalOpen(true)
  }

  const handleCategorySubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!categoryName.trim()) {
      showErrorToast("Category name is required")
      return
    }
    if (editingCategory) {
      updateCategoryMutation.mutate()
    } else {
      createCategoryMutation.mutate()
    }
  }

  const handleCreateTag = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTagName.trim()) return
    createTagMutation.mutate(newTagName)
  }

  return (
    <div className="flex flex-col gap-10">
      {/* Category Section */}
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Categories</h1>
            <p className="text-muted-foreground text-sm">
              Organize articles into main editorial sections (e.g. News,
              Academics, Sports, Events).
            </p>
          </div>
          <Button onClick={openCreateCategory} className="gap-2">
            <PlusCircle className="size-4" />
            Add Category
          </Button>
        </div>

        <div className="rounded-xl border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Category Name</TableHead>
                <TableHead>Slug</TableHead>
                <TableHead>Description</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loadingCategories ? (
                <TableRow>
                  <TableCell
                    colSpan={4}
                    className="h-32 text-center text-muted-foreground"
                  >
                    Loading categories...
                  </TableCell>
                </TableRow>
              ) : categories.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-32 text-center">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <FolderTree className="size-8 text-muted-foreground/50" />
                      <p className="font-medium text-sm">No categories yet</p>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                categories.map((cat) => (
                  <TableRow key={cat.id}>
                    <TableCell className="font-semibold">{cat.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-mono text-xs">
                        {cat.slug}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground max-w-md">
                      {cat.description || "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8"
                          onClick={() => openEditCategory(cat)}
                        >
                          <Edit className="size-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8 text-destructive hover:text-destructive"
                          onClick={() => setCategoryToDelete(cat)}
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Tags Section */}
      <div className="flex flex-col gap-6 border-t pt-8">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Tags</h2>
          <p className="text-muted-foreground text-sm">
            Keywords and topic tags applied across articles for
            cross-navigation.
          </p>
        </div>

        <form onSubmit={handleCreateTag} className="flex gap-2 max-w-sm">
          <Input
            placeholder="New tag name (e.g. academics)"
            value={newTagName}
            onChange={(e) => setNewTagName(e.target.value)}
          />
          <LoadingButton
            type="submit"
            loading={createTagMutation.isPending}
            disabled={!newTagName.trim()}
          >
            Add Tag
          </LoadingButton>
        </form>

        <div className="rounded-xl border bg-card p-6">
          {loadingTags ? (
            <p className="text-sm text-muted-foreground">Loading tags...</p>
          ) : tags.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
              <TagIcon className="size-6 mb-2 opacity-50" />
              <p className="text-sm">No tags created yet</p>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {tags.map((tag) => (
                <div
                  key={tag.id}
                  className="inline-flex items-center gap-1.5 rounded-full border bg-muted/40 px-3 py-1 text-xs font-medium text-foreground transition-colors hover:bg-muted"
                >
                  <span>#{tag.name}</span>
                  <button
                    type="button"
                    onClick={() => deleteTagMutation.mutate(tag.id)}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <X className="size-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Create / Edit Category Modal */}
      <Dialog open={categoryModalOpen} onOpenChange={setCategoryModalOpen}>
        <DialogContent>
          <form onSubmit={handleCategorySubmit}>
            <DialogHeader>
              <DialogTitle>
                {editingCategory ? "Edit Category" : "Add Category"}
              </DialogTitle>
              <DialogDescription>
                Categories group related articles on the website header and
                navigation.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="catName">Category Name</Label>
                <Input
                  id="catName"
                  placeholder="e.g. Sports"
                  value={categoryName}
                  onChange={(e) => setCategoryName(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="catDesc">Description</Label>
                <Textarea
                  id="catDesc"
                  placeholder="Articles covering sports events and athlete spotlights."
                  value={categoryDesc}
                  onChange={(e) => setCategoryDesc(e.target.value)}
                  rows={3}
                />
              </div>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setCategoryModalOpen(false)}
              >
                Cancel
              </Button>
              <LoadingButton
                type="submit"
                loading={
                  createCategoryMutation.isPending ||
                  updateCategoryMutation.isPending
                }
              >
                {editingCategory ? "Save Changes" : "Create Category"}
              </LoadingButton>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Category Confirmation Modal */}
      <Dialog
        open={!!categoryToDelete}
        onOpenChange={(open) => !open && setCategoryToDelete(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Category</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete category &ldquo;
              {categoryToDelete?.name}&rdquo;? Articles in this category will
              become uncategorized.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCategoryToDelete(null)}
              disabled={deleteCategoryMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() =>
                categoryToDelete &&
                deleteCategoryMutation.mutate(categoryToDelete.id)
              }
              disabled={deleteCategoryMutation.isPending}
            >
              {deleteCategoryMutation.isPending
                ? "Deleting..."
                : "Delete Category"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

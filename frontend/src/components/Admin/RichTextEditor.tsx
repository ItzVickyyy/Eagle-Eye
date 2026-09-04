import Image from "@tiptap/extension-image"
import Link from "@tiptap/extension-link"
import Placeholder from "@tiptap/extension-placeholder"
import Underline from "@tiptap/extension-underline"
import { EditorContent, useEditor } from "@tiptap/react"
import StarterKit from "@tiptap/starter-kit"
import {
  Bold,
  Code,
  FileCode,
  Heading2,
  Heading3,
  Heading4,
  Image as ImageIcon,
  Italic,
  Link as LinkIcon,
  List,
  ListOrdered,
  Minus,
  Quote,
  Redo,
  RemoveFormatting,
  Strikethrough,
  Underline as UnderlineIcon,
  Undo,
  Unlink,
  Upload,
} from "lucide-react"
import { useEffect, useState } from "react"

import { MediaService } from "@/client"
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
import { Separator } from "@/components/ui/separator"
import useCustomToast from "@/hooks/useCustomToast"
import { cn } from "@/lib/utils"

interface RichTextEditorProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  className?: string
  minHeight?: string
}

export function RichTextEditor({
  value,
  onChange,
  placeholder = "Write your story here...",
  disabled = false,
  className,
  minHeight = "min-h-[320px]",
}: RichTextEditorProps) {
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const [linkDialogOpen, setLinkDialogOpen] = useState(false)
  const [linkUrl, setLinkUrl] = useState("")

  const [imageDialogOpen, setImageDialogOpen] = useState(false)
  const [imageUrl, setImageUrl] = useState("")
  const [imageAlt, setImageAlt] = useState("")
  const [uploadingImage, setUploadingImage] = useState(false)

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [2, 3, 4],
        },
      }),
      Underline,
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          target: "_blank",
          rel: "noopener noreferrer",
          class: "text-primary underline underline-offset-4",
        },
      }),
      Image.configure({
        HTMLAttributes: {
          class: "rounded-lg max-w-full h-auto my-4 border",
        },
      }),
      Placeholder.configure({
        placeholder,
      }),
    ],
    content: value || "",
    editable: !disabled,
    onUpdate: ({ editor }) => {
      const html = editor.getHTML()
      const isEmpty =
        editor.isEmpty ||
        (!editor.getText().trim() && !html.includes("<img"))
      onChange(isEmpty ? "" : html)
    },
  })

  // Synchronize incoming value changes (e.g. async fetch on edit)
  useEffect(() => {
    if (!editor) return
    const currentHtml = editor.getHTML()
    const isEmpty =
      editor.isEmpty ||
      (!editor.getText().trim() && !currentHtml.includes("<img"))
    const normalizedCurrent = isEmpty ? "" : currentHtml
    const normalizedIncoming = value || ""

    if (normalizedIncoming !== normalizedCurrent) {
      editor.commands.setContent(normalizedIncoming)
    }
  }, [value, editor])

  useEffect(() => {
    if (!editor) return
    editor.setEditable(!disabled)
  }, [disabled, editor])

  if (!editor) {
    return (
      <div
        className={cn(
          "w-full rounded-md border border-input bg-background p-4 text-sm text-muted-foreground",
          minHeight,
          className
        )}
      >
        Loading editor...
      </div>
    )
  }

  const openLinkDialog = () => {
    const previousUrl = editor.getAttributes("link").href || ""
    setLinkUrl(previousUrl)
    setLinkDialogOpen(true)
  }

  const handleApplyLink = () => {
    if (!linkUrl.trim()) {
      editor.chain().focus().extendMarkRange("link").unsetLink().run()
    } else {
      let finalUrl = linkUrl.trim()
      if (
        !finalUrl.startsWith("http://") &&
        !finalUrl.startsWith("https://") &&
        !finalUrl.startsWith("mailto:") &&
        !finalUrl.startsWith("tel:") &&
        !finalUrl.startsWith("/")
      ) {
        finalUrl = `https://${finalUrl}`
      }
      editor
        .chain()
        .focus()
        .extendMarkRange("link")
        .setLink({ href: finalUrl })
        .run()
    }
    setLinkDialogOpen(false)
    setLinkUrl("")
  }

  const handleRemoveLink = () => {
    editor.chain().focus().unsetLink().run()
    setLinkDialogOpen(false)
    setLinkUrl("")
  }

  const handleImageFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploadingImage(true)
    try {
      const res: any = await MediaService.uploadFile({
        body: { file },
      })
      const uploadedUrl = res?.data?.file_url || res?.file_url
      if (uploadedUrl) {
        editor
          .chain()
          .focus()
          .setImage({ src: uploadedUrl, alt: file.name })
          .run()
        showSuccessToast("Image inserted successfully!")
        setImageDialogOpen(false)
        setImageUrl("")
        setImageAlt("")
      }
    } catch (err: any) {
      showErrorToast(err.message || "Failed to upload image")
    } finally {
      setUploadingImage(false)
    }
  }

  const handleInsertImageUrl = () => {
    if (!imageUrl.trim()) return
    editor
      .chain()
      .focus()
      .setImage({
        src: imageUrl.trim(),
        alt: imageAlt.trim() || undefined,
      })
      .run()
    setImageDialogOpen(false)
    setImageUrl("")
    setImageAlt("")
  }

  return (
    <div
      className={cn(
        "flex flex-col w-full rounded-md border border-input bg-background shadow-xs focus-within:ring-1 focus-within:ring-ring transition-colors",
        disabled && "opacity-60 cursor-not-allowed",
        className
      )}
    >
      {/* Formatting Toolbar */}
      <div
        role="toolbar"
        aria-label="Editor formatting options"
        className="flex flex-wrap items-center gap-1 border-b bg-muted/40 p-1.5 rounded-t-md text-muted-foreground"
      >
        {/* Headings */}
        <div className="flex items-center gap-0.5">
          <Button
            type="button"
            variant={editor.isActive("paragraph") ? "secondary" : "ghost"}
            size="sm"
            className="h-8 px-2 text-xs font-semibold"
            onClick={() => editor.chain().focus().setParagraph().run()}
            disabled={disabled}
            aria-label="Normal paragraph"
            title="Normal Paragraph"
          >
            P
          </Button>
          <Button
            type="button"
            variant={
              editor.isActive("heading", { level: 2 }) ? "secondary" : "ghost"
            }
            size="sm"
            className="h-8 px-2 text-xs font-semibold gap-1"
            onClick={() =>
              editor.chain().focus().toggleHeading({ level: 2 }).run()
            }
            disabled={disabled}
            aria-label="Heading 2"
            title="Heading 2 (H2)"
          >
            <Heading2 className="size-4" />
          </Button>
          <Button
            type="button"
            variant={
              editor.isActive("heading", { level: 3 }) ? "secondary" : "ghost"
            }
            size="sm"
            className="h-8 px-2 text-xs font-semibold gap-1"
            onClick={() =>
              editor.chain().focus().toggleHeading({ level: 3 }).run()
            }
            disabled={disabled}
            aria-label="Heading 3"
            title="Heading 3 (H3)"
          >
            <Heading3 className="size-4" />
          </Button>
          <Button
            type="button"
            variant={
              editor.isActive("heading", { level: 4 }) ? "secondary" : "ghost"
            }
            size="sm"
            className="h-8 px-2 text-xs font-semibold gap-1"
            onClick={() =>
              editor.chain().focus().toggleHeading({ level: 4 }).run()
            }
            disabled={disabled}
            aria-label="Heading 4"
            title="Heading 4 (H4)"
          >
            <Heading4 className="size-4" />
          </Button>
        </div>

        <Separator orientation="vertical" className="h-5 mx-1" />

        {/* Text Styles */}
        <div className="flex items-center gap-0.5">
          <Button
            type="button"
            variant={editor.isActive("bold") ? "secondary" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().toggleBold().run()}
            disabled={disabled}
            aria-label="Bold text"
            title="Bold (Ctrl+B)"
          >
            <Bold className="size-4" />
          </Button>
          <Button
            type="button"
            variant={editor.isActive("italic") ? "secondary" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().toggleItalic().run()}
            disabled={disabled}
            aria-label="Italic text"
            title="Italic (Ctrl+I)"
          >
            <Italic className="size-4" />
          </Button>
          <Button
            type="button"
            variant={editor.isActive("underline") ? "secondary" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().toggleUnderline().run()}
            disabled={disabled}
            aria-label="Underline text"
            title="Underline (Ctrl+U)"
          >
            <UnderlineIcon className="size-4" />
          </Button>
          <Button
            type="button"
            variant={editor.isActive("strike") ? "secondary" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().toggleStrike().run()}
            disabled={disabled}
            aria-label="Strikethrough text"
            title="Strikethrough"
          >
            <Strikethrough className="size-4" />
          </Button>
          <Button
            type="button"
            variant={editor.isActive("code") ? "secondary" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().toggleCode().run()}
            disabled={disabled}
            aria-label="Inline code"
            title="Inline Code"
          >
            <Code className="size-4" />
          </Button>
        </div>

        <Separator orientation="vertical" className="h-5 mx-1" />

        {/* Lists and Quotes */}
        <div className="flex items-center gap-0.5">
          <Button
            type="button"
            variant={editor.isActive("bulletList") ? "secondary" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            disabled={disabled}
            aria-label="Bullet list"
            title="Bullet List"
          >
            <List className="size-4" />
          </Button>
          <Button
            type="button"
            variant={editor.isActive("orderedList") ? "secondary" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            disabled={disabled}
            aria-label="Numbered list"
            title="Numbered List"
          >
            <ListOrdered className="size-4" />
          </Button>
          <Button
            type="button"
            variant={editor.isActive("blockquote") ? "secondary" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().toggleBlockquote().run()}
            disabled={disabled}
            aria-label="Blockquote"
            title="Blockquote"
          >
            <Quote className="size-4" />
          </Button>
          <Button
            type="button"
            variant={editor.isActive("codeBlock") ? "secondary" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().toggleCodeBlock().run()}
            disabled={disabled}
            aria-label="Code block"
            title="Code Block"
          >
            <FileCode className="size-4" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().setHorizontalRule().run()}
            disabled={disabled}
            aria-label="Horizontal rule"
            title="Horizontal Divider"
          >
            <Minus className="size-4" />
          </Button>
        </div>

        <Separator orientation="vertical" className="h-5 mx-1" />

        {/* Links & Images */}
        <div className="flex items-center gap-0.5">
          <Button
            type="button"
            variant={editor.isActive("link") ? "secondary" : "ghost"}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={openLinkDialog}
            disabled={disabled}
            aria-label="Insert or edit link"
            title="Link"
          >
            <LinkIcon className="size-4" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => setImageDialogOpen(true)}
            disabled={disabled}
            aria-label="Insert image"
            title="Insert Image"
          >
            <ImageIcon className="size-4" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().unsetAllMarks().clearNodes().run()}
            disabled={disabled}
            aria-label="Clear formatting"
            title="Clear Formatting"
          >
            <RemoveFormatting className="size-4" />
          </Button>
        </div>

        <Separator orientation="vertical" className="h-5 mx-1" />

        {/* History */}
        <div className="flex items-center gap-0.5 ml-auto">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().undo().run()}
            disabled={disabled || !editor.can().undo()}
            aria-label="Undo"
            title="Undo (Ctrl+Z)"
          >
            <Undo className="size-4" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => editor.chain().focus().redo().run()}
            disabled={disabled || !editor.can().redo()}
            aria-label="Redo"
            title="Redo (Ctrl+Y)"
          >
            <Redo className="size-4" />
          </Button>
        </div>
      </div>

      {/* Editor Content Area */}
      <div
        className={cn(
          "p-4 cursor-text overflow-y-auto focus-within:outline-hidden",
          minHeight
        )}
        onClick={() => editor.chain().focus().run()}
      >
        <EditorContent
          editor={editor}
          aria-label="Article content editor"
          className="prose-content min-h-[260px] text-base leading-relaxed text-foreground"
        />
      </div>

      {/* Link Dialog */}
      <Dialog open={linkDialogOpen} onOpenChange={setLinkDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Insert / Edit Link</DialogTitle>
            <DialogDescription>
              Enter the target web address or email for the selected text.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3 py-2">
            <Label htmlFor="link-url" className="text-xs font-semibold">
              URL
            </Label>
            <Input
              id="link-url"
              placeholder="https://example.com"
              value={linkUrl}
              onChange={(e) => setLinkUrl(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault()
                  handleApplyLink()
                }
              }}
            />
          </div>
          <DialogFooter className="flex items-center justify-between sm:justify-between">
            {editor.isActive("link") ? (
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={handleRemoveLink}
                className="gap-1.5"
              >
                <Unlink className="size-4" />
                Remove Link
              </Button>
            ) : (
              <div />
            )}
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setLinkDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button type="button" size="sm" onClick={handleApplyLink}>
                Save Link
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Image Dialog */}
      <Dialog open={imageDialogOpen} onOpenChange={setImageDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Insert Image</DialogTitle>
            <DialogDescription>
              Upload an image from your device or specify an image URL.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-4 py-2">
            {/* File upload option */}
            <div className="flex flex-col gap-2">
              <Label className="text-xs font-semibold">Upload Image</Label>
              <label className="cursor-pointer border border-dashed rounded-lg p-4 flex flex-col items-center justify-center gap-2 hover:bg-muted/30 transition-colors">
                <Upload className="size-6 text-muted-foreground" />
                <span className="text-xs font-medium text-foreground">
                  {uploadingImage ? "Uploading image..." : "Choose image to upload"}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  PNG, JPG, WEBP or GIF
                </span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageFileUpload}
                  disabled={uploadingImage}
                  className="sr-only"
                />
              </label>
            </div>

            <div className="relative flex items-center justify-center">
              <Separator className="w-full" />
              <span className="absolute bg-background px-2 text-[11px] text-muted-foreground uppercase">
                Or via URL
              </span>
            </div>

            {/* URL option */}
            <div className="flex flex-col gap-2">
              <Label htmlFor="image-url-input" className="text-xs font-semibold">
                Image Web URL
              </Label>
              <Input
                id="image-url-input"
                placeholder="https://example.com/photo.jpg"
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="image-alt-input" className="text-xs font-semibold">
                Alt Text / Caption (Optional)
              </Label>
              <Input
                id="image-alt-input"
                placeholder="Description of the image"
                value={imageAlt}
                onChange={(e) => setImageAlt(e.target.value)}
              />
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setImageDialogOpen(false)}
            >
              Cancel
            </Button>
            <LoadingButton
              type="button"
              size="sm"
              loading={uploadingImage}
              disabled={!imageUrl.trim()}
              onClick={handleInsertImageUrl}
            >
              Insert URL
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

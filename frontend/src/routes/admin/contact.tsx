import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import {
  Eye,
  Inbox,
  Mail,
  MailCheck,
  MailOpen,
  Search,
  ShieldAlert,
  Trash2,
} from "lucide-react"
import { useState } from "react"

import { ContactService, type ContactMessageStatus } from "@/client"
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
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { formatDate } from "@/utils"

export const Route = createFileRoute("/admin/contact")({
  component: ContactInbox,
  head: () => ({
    meta: [{ title: "Contact Inbox — Eagle Eye" }],
  }),
})

const statusBadgeVariants: Record<
  string,
  { label: string; className: string }
> = {
  new: {
    label: "Unread",
    className:
      "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20 font-semibold",
  },
  read: {
    label: "Read",
    className:
      "bg-muted text-muted-foreground border-border",
  },
}

function ContactInbox() {
  const { user: currentUser } = useAuth()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const [activeTab, setActiveTab] = useState<string>("all")
  const [searchQuery, setSearchQuery] = useState<string>("")
  const [selectedMessage, setSelectedMessage] = useState<any | null>(null)
  const [messageToDelete, setMessageToDelete] = useState<any | null>(null)

  const isStaffAdmin =
    currentUser?.is_superuser ||
    currentUser?.role === "super_admin" ||
    currentUser?.role === "admin"

  const { data: messagesRes, isLoading } = useQuery({
    queryKey: ["admin-contact-messages", activeTab],
    queryFn: () =>
      ContactService.readContactMessages({
        query: {
          status:
            activeTab === "all"
              ? undefined
              : (activeTab as ContactMessageStatus),
          limit: 100,
        },
      }),
    enabled: !!isStaffAdmin,
  })

  const markReadMutation = useMutation({
    mutationFn: (id: number) =>
      ContactService.markMessageRead({ path: { id } }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["admin-contact-messages"] })
      if (selectedMessage && selectedMessage.id === (updated as any)?.id) {
        setSelectedMessage({ ...selectedMessage, status: "read" })
      }
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to update message state")
    },
  })

  const markUnreadMutation = useMutation({
    mutationFn: (id: number) =>
      ContactService.markMessageUnread({ path: { id } }),
    onSuccess: (updated) => {
      showSuccessToast("Message marked as unread")
      queryClient.invalidateQueries({ queryKey: ["admin-contact-messages"] })
      if (selectedMessage && selectedMessage.id === (updated as any)?.id) {
        setSelectedMessage({ ...selectedMessage, status: "new" })
      }
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to mark as unread")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) =>
      ContactService.deleteContactMessage({ path: { id } }),
    onSuccess: () => {
      showSuccessToast("Message deleted successfully")
      setMessageToDelete(null)
      if (selectedMessage?.id === messageToDelete?.id) {
        setSelectedMessage(null)
      }
      queryClient.invalidateQueries({ queryKey: ["admin-contact-messages"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to delete message")
    },
  })

  const handleOpenMessage = (msg: any) => {
    setSelectedMessage(msg)
    if (msg.status === "new") {
      markReadMutation.mutate(msg.id)
    }
  }

  if (!isStaffAdmin) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center">
        <ShieldAlert className="size-12 text-destructive mb-3" />
        <h2 className="text-xl font-bold">Access Restricted</h2>
        <p className="text-muted-foreground text-sm mt-1 max-w-md">
          Viewing the Contact Inbox requires Administrator privileges.
        </p>
      </div>
    )
  }

  const rawMessages: any[] =
    (messagesRes?.data as any)?.data || (messagesRes as any)?.data || []

  const filteredMessages = rawMessages.filter((m) => {
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase()
    return (
      m.name?.toLowerCase().includes(q) ||
      m.email?.toLowerCase().includes(q) ||
      m.subject?.toLowerCase().includes(q) ||
      m.message?.toLowerCase().includes(q)
    )
  })

  const unreadCount = rawMessages.filter((m) => m.status === "new").length

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">Contact Inbox</h1>
            {unreadCount > 0 && (
              <Badge className="bg-primary text-primary-foreground text-xs">
                {unreadCount} unread
              </Badge>
            )}
          </div>
          <p className="text-muted-foreground text-sm">
            Read and manage general inquiries and feedback sent through the public contact form.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="w-full sm:w-auto"
        >
          <TabsList>
            <TabsTrigger value="all">All Messages</TabsTrigger>
            <TabsTrigger value="new">
              Unread {unreadCount > 0 && `(${unreadCount})`}
            </TabsTrigger>
            <TabsTrigger value="read">Read</TabsTrigger>
          </TabsList>
        </Tabs>

        <div className="relative w-full sm:w-72">
          <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
          <Input
            placeholder="Search sender, subject, message..."
            className="pl-9 text-xs"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Messages Table */}
      <div className="rounded-md border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[180px]">Sender</TableHead>
              <TableHead className="w-[200px]">Subject</TableHead>
              <TableHead className="min-w-[240px]">Message Preview</TableHead>
              <TableHead className="w-[100px]">Status</TableHead>
              <TableHead className="w-[130px]">Received</TableHead>
              <TableHead className="w-[140px] text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center text-muted-foreground">
                  Loading messages...
                </TableCell>
              </TableRow>
            ) : filteredMessages.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center text-muted-foreground">
                  <div className="flex flex-col items-center justify-center gap-1.5">
                    <Inbox className="size-6 text-muted-foreground/60" />
                    <span>No contact messages found</span>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              filteredMessages.map((m) => {
                const badge =
                  statusBadgeVariants[m.status] || statusBadgeVariants.read
                const isUnread = m.status === "new"
                return (
                  <TableRow
                    key={m.id}
                    className={isUnread ? "bg-primary/5 font-medium" : undefined}
                  >
                    <TableCell className="align-top">
                      <div className="flex flex-col">
                        <span className="text-sm font-semibold text-foreground">
                          {m.name}
                        </span>
                        <a
                          href={`mailto:${m.email}`}
                          className="text-xs text-muted-foreground hover:underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {m.email}
                        </a>
                      </div>
                    </TableCell>
                    <TableCell className="align-top text-xs font-medium">
                      <span className="line-clamp-2">
                        {m.subject || "(No subject)"}
                      </span>
                    </TableCell>
                    <TableCell className="align-top">
                      <p
                        className="text-xs text-muted-foreground line-clamp-2 cursor-pointer hover:text-foreground transition-colors"
                        onClick={() => handleOpenMessage(m)}
                      >
                        {m.message}
                      </p>
                    </TableCell>
                    <TableCell className="align-top">
                      <Badge variant="outline" className={badge.className}>
                        {badge.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="align-top text-xs text-muted-foreground whitespace-nowrap">
                      {formatDate(m.sent_at)}
                    </TableCell>
                    <TableCell className="align-top text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8"
                          title="View Message"
                          onClick={() => handleOpenMessage(m)}
                        >
                          <Eye className="size-4" />
                        </Button>
                        {m.status === "new" ? (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-8 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-500/10"
                            title="Mark as Read"
                            disabled={markReadMutation.isPending}
                            onClick={() => markReadMutation.mutate(m.id)}
                          >
                            <MailOpen className="size-4" />
                          </Button>
                        ) : (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-8 text-muted-foreground hover:text-foreground"
                            title="Mark as Unread"
                            disabled={markUnreadMutation.isPending}
                            onClick={() => markUnreadMutation.mutate(m.id)}
                          >
                            <Mail className="size-4" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                          title="Delete Message"
                          onClick={() => setMessageToDelete(m)}
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* View Message Details Dialog */}
      <Dialog
        open={!!selectedMessage}
        onOpenChange={(open) => {
          if (!open) setSelectedMessage(null)
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <div className="flex items-center justify-between pr-6">
              <DialogTitle className="text-lg font-bold">
                {selectedMessage?.subject || "Contact Inquiry"}
              </DialogTitle>
              {selectedMessage && (
                <Badge
                  variant="outline"
                  className={
                    (statusBadgeVariants[selectedMessage.status] ||
                      statusBadgeVariants.read).className
                  }
                >
                  {(statusBadgeVariants[selectedMessage.status] ||
                    statusBadgeVariants.read).label}
                </Badge>
              )}
            </div>
            <DialogDescription className="text-xs">
              Received on {formatDate(selectedMessage?.sent_at)}
            </DialogDescription>
          </DialogHeader>

          {selectedMessage && (
            <div className="flex flex-col gap-4 py-2">
              <div className="rounded-lg border bg-muted/30 p-3 flex flex-col gap-1 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-foreground">
                    {selectedMessage.name}
                  </span>
                  <a
                    href={`mailto:${selectedMessage.email}?subject=Re: ${encodeURIComponent(
                      selectedMessage.subject || "Your message to Eagle Eye"
                    )}`}
                    className="text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Reply via email <MailCheck className="size-3.5" />
                  </a>
                </div>
                <span className="text-muted-foreground">
                  {selectedMessage.email}
                </span>
              </div>

              <div className="flex flex-col gap-1.5">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Message
                </span>
                {/* Secure Plain Text Rendering with whitespace-pre-wrap - NOT HTML */}
                <div className="rounded-md border bg-card p-4 text-sm text-foreground whitespace-pre-wrap leading-relaxed max-h-72 overflow-y-auto">
                  {selectedMessage.message}
                </div>
              </div>
            </div>
          )}

          <DialogFooter className="flex items-center justify-between sm:justify-between">
            <Button
              variant="destructive"
              size="sm"
              onClick={() => {
                const target = selectedMessage
                setMessageToDelete(target)
              }}
              className="gap-1.5"
            >
              <Trash2 className="size-4" />
              Delete
            </Button>

            <div className="flex items-center gap-2">
              {selectedMessage?.status === "read" ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => markUnreadMutation.mutate(selectedMessage.id)}
                >
                  Mark Unread
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => markReadMutation.mutate(selectedMessage.id)}
                >
                  Mark Read
                </Button>
              )}
              <Button
                size="sm"
                onClick={() => setSelectedMessage(null)}
              >
                Close
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={!!messageToDelete}
        onOpenChange={(open) => {
          if (!open) setMessageToDelete(null)
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete Contact Message</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this message from{" "}
              <strong>{messageToDelete?.name}</strong>? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>

          {messageToDelete && (
            <div className="rounded-md border bg-muted/40 p-3 text-xs text-foreground/80 line-clamp-3">
              "{messageToDelete.message}"
            </div>
          )}

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setMessageToDelete(null)}
            >
              Cancel
            </Button>
            <LoadingButton
              variant="destructive"
              size="sm"
              loading={deleteMutation.isPending}
              onClick={() => {
                if (messageToDelete?.id) {
                  deleteMutation.mutate(messageToDelete.id)
                }
              }}
            >
              Delete
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

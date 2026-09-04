import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import {
  Edit,
  PlusCircle,
  Trash2,
  Upload,
  UserCheck,
  UserX,
  Users,
} from "lucide-react"
import { useState } from "react"

import { ClubMembersService, MediaService, UsersService } from "@/client"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
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
import useCustomToast from "@/hooks/useCustomToast"
import { getInitials } from "@/utils"

export const Route = createFileRoute("/admin/members")({
  component: Members,
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    const isSuperAdmin = user.is_superuser || user.role === "super_admin"
    if (!isSuperAdmin) {
      throw redirect({
        to: "/admin",
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Members — Eagle Eye",
      },
    ],
  }),
})

function Members() {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const [modalOpen, setModalOpen] = useState(false)
  const [editingMember, setEditingMember] = useState<any | null>(null)
  const [memberToDelete, setMemberToDelete] = useState<any | null>(null)
  const [uploadingPhoto, setUploadingPhoto] = useState(false)

  // Form states
  const [firstName, setFirstName] = useState("")
  const [lastName, setLastName] = useState("")
  const [position, setPosition] = useState("")
  const [department, setDepartment] = useState("")
  const [photoUrl, setPhotoUrl] = useState("")
  const [isOfficer, setIsOfficer] = useState(false)
  const [isActive, setIsActive] = useState(true)
  const [sortOrder, setSortOrder] = useState(0)

  const { data: membersRes, isLoading } = useQuery({
    queryKey: ["admin-club-members"],
    queryFn: () => ClubMembersService.membersReadAllMembers(),
  })

  const members: any[] =
    (membersRes?.data as any)?.data || (membersRes as any)?.data || []

  // Mutations
  const createMutation = useMutation({
    mutationFn: () =>
      ClubMembersService.membersCreateClubMember({
        body: {
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          position: position.trim() || undefined,
          position_title: position.trim() || undefined,
          department: department.trim() || undefined,
          photo_url: photoUrl.trim() || undefined,
          is_officer: isOfficer,
          is_active: isActive,
          sort_order: Number(sortOrder) || 0,
        },
      }),
    onSuccess: () => {
      showSuccessToast("Member added successfully")
      setModalOpen(false)
      resetForm()
      queryClient.invalidateQueries({ queryKey: ["admin-club-members"] })
      queryClient.invalidateQueries({ queryKey: ["active-club-members"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to add member")
    },
  })

  const updateMutation = useMutation({
    mutationFn: () =>
      ClubMembersService.membersUpdateClubMember({
        path: { id: editingMember.id },
        body: {
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          position: position.trim() || undefined,
          position_title: position.trim() || undefined,
          department: department.trim() || undefined,
          photo_url: photoUrl.trim() || undefined,
          is_officer: isOfficer,
          is_active: isActive,
          sort_order: Number(sortOrder) || 0,
        },
      }),
    onSuccess: () => {
      showSuccessToast("Member updated successfully")
      setModalOpen(false)
      resetForm()
      queryClient.invalidateQueries({ queryKey: ["admin-club-members"] })
      queryClient.invalidateQueries({ queryKey: ["active-club-members"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to update member")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) =>
      ClubMembersService.membersDeleteClubMember({ path: { id } }),
    onSuccess: () => {
      showSuccessToast("Member deleted successfully")
      setMemberToDelete(null)
      queryClient.invalidateQueries({ queryKey: ["admin-club-members"] })
      queryClient.invalidateQueries({ queryKey: ["active-club-members"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to delete member")
    },
  })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      ClubMembersService.membersUpdateClubMember({
        path: { id },
        body: { is_active },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-club-members"] })
      queryClient.invalidateQueries({ queryKey: ["active-club-members"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to toggle status")
    },
  })

  const resetForm = () => {
    setEditingMember(null)
    setFirstName("")
    setLastName("")
    setPosition("")
    setDepartment("")
    setPhotoUrl("")
    setIsOfficer(false)
    setIsActive(true)
    setSortOrder(0)
  }

  const openCreate = () => {
    resetForm()
    setModalOpen(true)
  }

  const openEdit = (member: any) => {
    setEditingMember(member)
    setFirstName(member.first_name || "")
    setLastName(member.last_name || "")
    setPosition(member.position_title || member.position || "")
    setDepartment(member.department || "")
    setPhotoUrl(member.photo_url || "")
    setIsOfficer(!!member.is_officer)
    setIsActive(member.is_active !== false)
    setSortOrder(member.sort_order || 0)
    setModalOpen(true)
  }

  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploadingPhoto(true)
    try {
      const res: any = await MediaService.uploadFile({
        body: { file },
      })
      const url = res?.data?.file_url || res?.file_url
      if (url) {
        setPhotoUrl(url)
        showSuccessToast("Photo uploaded!")
      }
    } catch (err: any) {
      showErrorToast(err.message || "Failed to upload photo")
    } finally {
      setUploadingPhoto(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!firstName.trim() || !lastName.trim()) {
      showErrorToast("First name and last name are required")
      return
    }
    if (editingMember) {
      updateMutation.mutate()
    } else {
      createMutation.mutate()
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Club Members</h1>
          <p className="text-muted-foreground text-sm">
            Manage the student editorial board, officers, and faculty advisers displayed on the About Us page.
          </p>
        </div>
        <Button onClick={openCreate} className="gap-2">
          <PlusCircle className="size-4" />
          Add Member
        </Button>
      </div>

      <div className="rounded-xl border bg-card overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Member</TableHead>
              <TableHead>Position / Role</TableHead>
              <TableHead>Department</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center text-muted-foreground">
                  Loading members...
                </TableCell>
              </TableRow>
            ) : members.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center">
                  <div className="flex flex-col items-center justify-center gap-2">
                    <Users className="size-8 text-muted-foreground/50" />
                    <p className="font-medium text-sm">No members added yet</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              members.map((member) => {
                const fullName = `${member.first_name} ${member.last_name}`
                const initials = getInitials(fullName)

                return (
                  <TableRow key={member.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <Avatar className="size-9">
                          {member.photo_url && (
                            <AvatarImage src={member.photo_url} alt={fullName} />
                          )}
                          <AvatarFallback className="text-xs">
                            {initials}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <p className="font-semibold text-sm">{fullName}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm font-medium">
                      {member.position_title || member.position || "Staff"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {member.department || "—"}
                    </TableCell>
                    <TableCell>
                      {member.is_officer ? (
                        <Badge className="bg-primary/10 text-primary border-primary/20 text-xs">
                          Officer
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs">
                          Member
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <button
                        type="button"
                        onClick={() =>
                          toggleActiveMutation.mutate({
                            id: member.id,
                            is_active: !member.is_active,
                          })
                        }
                        className="inline-flex items-center gap-1.5 cursor-pointer text-xs"
                      >
                        {member.is_active !== false ? (
                          <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20">
                            <UserCheck className="size-3 mr-1" /> Active
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="hover:bg-muted">
                            <UserX className="size-3 mr-1" /> Inactive
                          </Badge>
                        )}
                      </button>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8"
                          onClick={() => openEdit(member)}
                        >
                          <Edit className="size-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8 text-destructive hover:text-destructive"
                          onClick={() => setMemberToDelete(member)}
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

      {/* Create / Edit Member Dialog */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-md">
          <form onSubmit={handleSubmit}>
            <DialogHeader>
              <DialogTitle>
                {editingMember ? "Edit Club Member" : "Add Club Member"}
              </DialogTitle>
              <DialogDescription>
                Add member details to display in the About Us leadership & staff list.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="firstName">First Name *</Label>
                  <Input
                    id="firstName"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName">Last Name *</Label>
                  <Input
                    id="lastName"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="pos">Position / Title</Label>
                <Input
                  id="pos"
                  placeholder="e.g. Editor-in-Chief, Adviser, Layout Artist"
                  value={position}
                  onChange={(e) => setPosition(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="dept">Department / Strand</Label>
                <Input
                  id="dept"
                  placeholder="e.g. Editorial, Multimedia, HUMSS"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                />
              </div>

              {/* Photo */}
              <div className="space-y-2">
                <Label>Member Photo</Label>
                <div className="flex items-center gap-3">
                  <Avatar className="size-12 border">
                    {photoUrl && <AvatarImage src={photoUrl} />}
                    <AvatarFallback className="text-xs">
                      {getInitials(firstName + " " + lastName) || "?"}
                    </AvatarFallback>
                  </Avatar>
                  <label className="cursor-pointer">
                    <span className="inline-flex items-center gap-1.5 rounded-md border bg-background px-3 py-1.5 text-xs font-medium hover:bg-accent">
                      <Upload className="size-3.5" />
                      {uploadingPhoto ? "Uploading..." : "Upload Photo"}
                    </span>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handlePhotoUpload}
                      disabled={uploadingPhoto}
                      className="sr-only"
                    />
                  </label>
                  {photoUrl && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setPhotoUrl("")}
                      className="text-xs text-destructive h-8"
                    >
                      Clear
                    </Button>
                  )}
                </div>
                <Input
                  placeholder="Or direct image URL..."
                  value={photoUrl}
                  onChange={(e) => setPhotoUrl(e.target.value)}
                  className="text-xs mt-1"
                />
              </div>

              <div className="flex items-center gap-6 pt-2">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="isOfficer"
                    checked={isOfficer}
                    onCheckedChange={(checked) => setIsOfficer(!!checked)}
                  />
                  <Label htmlFor="isOfficer" className="text-xs font-normal">
                    Officer / Adviser
                  </Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="isActive"
                    checked={isActive}
                    onCheckedChange={(checked) => setIsActive(!!checked)}
                  />
                  <Label htmlFor="isActive" className="text-xs font-normal">
                    Active Member
                  </Label>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setModalOpen(false)}
              >
                Cancel
              </Button>
              <LoadingButton
                type="submit"
                loading={createMutation.isPending || updateMutation.isPending}
              >
                {editingMember ? "Save Changes" : "Add Member"}
              </LoadingButton>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog
        open={!!memberToDelete}
        onOpenChange={(open) => !open && setMemberToDelete(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Member</DialogTitle>
            <DialogDescription>
              Are you sure you want to remove{" "}
              {memberToDelete?.first_name} {memberToDelete?.last_name} from the club directory?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setMemberToDelete(null)}
              disabled={deleteMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() =>
                memberToDelete && deleteMutation.mutate(memberToDelete.id)
              }
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

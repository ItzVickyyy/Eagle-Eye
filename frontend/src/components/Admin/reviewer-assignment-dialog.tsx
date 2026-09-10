import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import {
  ReviewAssignmentsService,
  UsersService,
  type ReviewAssignmentDetailPublic,
  type UserPublic,
} from "@/client"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { getInitials } from "@/utils"
import { UserMinus, UserPlus } from "lucide-react"

interface ReviewerAssignmentDialogProps {
  articleId: string
  articleHeadline: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ReviewerAssignmentDialog({
  articleId,
  articleHeadline,
  open,
  onOpenChange,
}: ReviewerAssignmentDialogProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [selectedReviewerId, setSelectedReviewerId] = useState<string>("")

  const { data: assignmentsRes, isLoading: isLoadingAssignments } = useQuery({
    queryKey: ["review-assignments", articleId],
    queryFn: () =>
      ReviewAssignmentsService.assignmentsListAssignmentsForArticle({
        path: { article_id: articleId },
      }),
    enabled: open,
  })

  const { data: usersRes, isLoading: isLoadingUsers } = useQuery({
    queryKey: ["users-list"],
    queryFn: () => UsersService.readUsers(),
    enabled: open,
  })

  const assignments: ReviewAssignmentDetailPublic[] =
    (assignmentsRes?.data as any)?.data || []

  const users: UserPublic[] =
    (usersRes?.data as any)?.data || []

  const eligibleReviewers = users.filter(
    (u) =>
      u.is_active &&
      (u.role === "admin" || u.role === "super_admin"),
  )

  const createAssignmentMutation = useMutation({
    mutationFn: (reviewerId: string) =>
      ReviewAssignmentsService.assignmentsCreateAssignment({
        body: {
          article_id: articleId,
          reviewer_id: reviewerId,
          notes: "Assigned from review queue",
        },
      }),
    onSuccess: () => {
      showSuccessToast("Reviewer assigned successfully")
      setSelectedReviewerId("")
      queryClient.invalidateQueries({ queryKey: ["review-assignments", articleId] })
      queryClient.invalidateQueries({ queryKey: ["review-queue"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to assign reviewer")
    },
  })

  const removeAssignmentMutation = useMutation({
    mutationFn: (assignmentId: string) =>
      ReviewAssignmentsService.assignmentsRemoveAssignment({
        path: { assignment_id: assignmentId },
      }),
    onSuccess: () => {
      showSuccessToast("Assignment removed")
      queryClient.invalidateQueries({ queryKey: ["review-assignments", articleId] })
      queryClient.invalidateQueries({ queryKey: ["review-queue"] })
    },
    onError: (err: any) => {
      showErrorToast(err.message || "Failed to remove assignment")
    },
  })

  const handleAssign = () => {
    if (!selectedReviewerId) return
    createAssignmentMutation.mutate(selectedReviewerId)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Manage Reviewer Assignment</DialogTitle>
          <DialogDescription className="line-clamp-1">
            {articleHeadline}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Current Assignments */}
          <div>
            <h4 className="text-sm font-medium mb-2">Current Assignments</h4>
            {isLoadingAssignments ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : assignments.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No reviewer assigned yet
              </p>
            ) : (
              <div className="space-y-2">
                {assignments
                  .filter((a) => a.status === "active")
                  .map((assignment) => {
                    const reviewer = assignment.reviewer
                    const reviewerName =
                      reviewer?.full_name || reviewer?.email || "Unknown"
                    return (
                      <div
                        key={assignment.id}
                        className="flex items-center justify-between p-2 rounded-lg bg-muted/50"
                      >
                        <div className="flex items-center gap-2">
                          <Avatar className="size-7">
                            <AvatarFallback className="text-xs">
                              {getInitials(reviewerName)}
                            </AvatarFallback>
                          </Avatar>
                          <div className="text-sm">
                            <p className="font-medium">{reviewerName}</p>
                            <p className="text-xs text-muted-foreground">
                              {reviewer?.role || "Reviewer"}
                            </p>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                          onClick={() =>
                            removeAssignmentMutation.mutate(assignment.id)
                          }
                          disabled={removeAssignmentMutation.isPending}
                        >
                          <UserMinus className="size-4" />
                        </Button>
                      </div>
                    )
                  })}
              </div>
            )}
          </div>

          {/* Add New Assignment */}
          <div>
            <h4 className="text-sm font-medium mb-2">Assign Reviewer</h4>
            <div className="flex gap-2">
              <Select
                value={selectedReviewerId}
                onValueChange={setSelectedReviewerId}
                disabled={isLoadingUsers}
              >
                <SelectTrigger className="flex-1">
                  <SelectValue
                    placeholder={
                      isLoadingUsers ? "Loading users..." : "Select a reviewer"
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  {eligibleReviewers.map((user) => (
                    <SelectItem key={user.id} value={user.id}>
                      {user.full_name || user.email} ({user.role})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <LoadingButton
                onClick={handleAssign}
                disabled={!selectedReviewerId}
                loading={createAssignmentMutation.isPending}
                size="sm"
              >
                <UserPlus className="size-4 mr-1" />
                Assign
              </LoadingButton>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

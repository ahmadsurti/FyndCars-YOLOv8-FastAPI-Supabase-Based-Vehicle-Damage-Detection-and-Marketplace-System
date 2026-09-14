import { useNavigate } from '@tanstack/react-router'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/lib/auth/auth-store'

type SignOutDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SignOutDialog({ open, onOpenChange }: SignOutDialogProps) {
  const navigate = useNavigate()
  const { signOut } = useAuthStore()

  const handleSignOut = async () => {
    await signOut()
    onOpenChange(false)
    navigate({ to: '/' })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md bg-[#08090c] border border-white/[0.08] text-foreground">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold tracking-tight text-white">
            Terminate Session?
          </DialogTitle>
          <DialogDescription className="text-sm text-neutral-400">
            Are you sure you want to sign out? You will need to re-authenticate to access your saved inventory and seller garage.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:gap-0 mt-4">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="border-white/[0.1] text-neutral-300 hover:bg-white/[0.05]"
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleSignOut}
            className="bg-red-500/90 text-white hover:bg-red-600"
          >
            Sign Out
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

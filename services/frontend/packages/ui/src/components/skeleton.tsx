import { cn } from "../lib/utils"

// shadcn/ui new-york-v4 (MIT; see NOTICE), unchanged but for the import path.
function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn("animate-pulse rounded-md bg-accent", className)}
      {...props}
    />
  )
}

export { Skeleton }

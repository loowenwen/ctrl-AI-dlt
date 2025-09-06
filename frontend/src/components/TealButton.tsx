// src/components/TealButton.tsx
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface TealButtonProps extends React.ComponentProps<typeof Button> {}

export function TealButton({ className, size, ...props }: TealButtonProps) {
  return (
    <Button
      {...props}
      size={size}
      className={cn(
        "bg-[#1f8088] hover:bg-teal-700 text-white font-medium",
        className
      )}
    />
  )
}
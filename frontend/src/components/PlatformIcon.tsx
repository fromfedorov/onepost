import { Send } from "lucide-react"
import type { Platform } from "@/lib/types"
import { cn } from "@/lib/utils"

interface Props {
  platform: Platform
  className?: string
}

function LinkedinIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M20.45 20.45h-3.55v-5.57c0-1.33-.03-3.04-1.86-3.04-1.86 0-2.15 1.45-2.15 2.95v5.66H9.34V9h3.41v1.56h.05c.47-.9 1.63-1.85 3.36-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.06 2.06 0 11.001-4.121 2.06 2.06 0 010 4.121zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.72v20.56C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.72V1.72C24 .77 23.2 0 22.22 0z" />
    </svg>
  )
}

export function PlatformIcon({ platform, className }: Props) {
  if (platform === "linkedin") {
    return <LinkedinIcon className={cn("h-4 w-4 text-[#0a66c2]", className)} />
  }
  return <Send className={cn("h-4 w-4 text-[#229ed9]", className)} />
}

export function platformLabel(platform: Platform): string {
  return platform === "linkedin" ? "LinkedIn" : "Telegram"
}

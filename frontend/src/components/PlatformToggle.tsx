import { Switch } from "@/components/ui/switch"
import { PlatformIcon, platformLabel } from "@/components/PlatformIcon"
import type { Platform } from "@/lib/types"

interface Props {
  platform: Platform
  caption: string
  enabled: boolean
  onChange: (enabled: boolean) => void
}

export function PlatformToggle({ platform, caption, enabled, onChange }: Props) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-border px-3 py-2.5">
      <div className="flex items-center gap-3">
        <PlatformIcon platform={platform} className="h-5 w-5" />
        <div className="flex flex-col">
          <span className="text-sm font-medium">{platformLabel(platform)}</span>
          <span className="text-xs text-muted-foreground">{caption}</span>
        </div>
      </div>
      <Switch checked={enabled} onCheckedChange={onChange} />
    </div>
  )
}

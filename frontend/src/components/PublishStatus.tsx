import { CheckCircle2, Loader2, RefreshCw, XCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { PlatformIcon, platformLabel } from "@/components/PlatformIcon"
import type { PlatformPost, Platform } from "@/lib/types"

interface Props {
  platformPosts: PlatformPost[]
  onRetry: (platform: Platform) => void
}

export function PublishStatus({ platformPosts, onRetry }: Props) {
  if (platformPosts.length === 0) return null
  return (
    <div className="flex flex-col gap-2">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        Результат публикации
      </div>
      {platformPosts.map((pp) => (
        <StatusRow key={pp.id} pp={pp} onRetry={() => onRetry(pp.platform)} />
      ))}
    </div>
  )
}

function StatusRow({ pp, onRetry }: { pp: PlatformPost; onRetry: () => void }) {
  const loading = pp.status === "queued" || pp.status === "publishing"
  const success = pp.status === "succeeded"
  const error = pp.status === "failed" || pp.status === "permanently_failed"

  let bg = "bg-muted"
  if (success) bg = "bg-[color-mix(in_oklab,var(--color-success)_15%,var(--color-background))]"
  if (error) bg = "bg-[color-mix(in_oklab,var(--color-destructive)_15%,var(--color-background))]"

  return (
    <div className={`rounded-md border border-border px-3 py-2 ${bg}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <PlatformIcon platform={pp.platform} className="h-4 w-4" />
          <span className="text-sm font-medium">{platformLabel(pp.platform)}</span>
        </div>
        <div className="flex items-center gap-2">
          {loading && (
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              {pp.status === "publishing" ? "Отправляем…" : "В очереди"}
            </span>
          )}
          {success && (
            <span className="flex items-center gap-1.5 text-xs">
              <CheckCircle2 className="h-3.5 w-3.5 text-[oklch(0.62_0.17_142)]" />
              Опубликовано
              {pp.external_url && (
                <a
                  href={pp.external_url}
                  target="_blank"
                  rel="noopener"
                  className="underline ml-1"
                >
                  открыть
                </a>
              )}
            </span>
          )}
          {error && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 gap-1 text-xs"
              onClick={onRetry}
            >
              <RefreshCw className="h-3 w-3" />
              Повторить
            </Button>
          )}
        </div>
      </div>
      {error && (
        <div className="mt-1.5 flex items-start gap-1.5 text-xs">
          <XCircle className="h-3.5 w-3.5 mt-0.5 text-destructive shrink-0" />
          <span className="text-destructive">{pp.last_error ?? "Не удалось опубликовать"}</span>
        </div>
      )}
      {pp.attempts > 1 && (
        <div className="mt-1 text-[11px] text-muted-foreground">
          Попыток: {pp.attempts}
        </div>
      )}
    </div>
  )
}

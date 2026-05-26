import { CheckCircle2, Clock, XCircle, Loader2, Ban, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { PlatformIcon, platformLabel } from "@/components/PlatformIcon"
import type { PlatformPost, Post } from "@/lib/types"

interface Props {
  posts: Post[]
  onCancel: (postId: string) => void
}

export function History({ posts, onCancel }: Props) {
  if (posts.length === 0) {
    return (
      <Card className="p-4 text-sm text-muted-foreground text-center">
        Пока ничего не опубликовано.
      </Card>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        История
      </div>
      {posts.map((p) => (
        <HistoryRow key={p.id} post={p} onCancel={() => onCancel(p.id)} />
      ))}
    </div>
  )
}

function HistoryRow({ post, onCancel }: { post: Post; onCancel: () => void }) {
  const scheduled = post.state === "scheduled"
  const created = new Date(post.created_at)
  const when = scheduled && post.scheduled_at ? new Date(post.scheduled_at) : created

  return (
    <Card className="p-3 flex flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm whitespace-pre-wrap line-clamp-3 flex-1">{post.content}</p>
        {scheduled && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs text-muted-foreground"
            onClick={onCancel}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
          {scheduled && <Clock className="h-3 w-3" />}
          <span>
            {scheduled ? "Запланировано на " : ""}
            {when.toLocaleString()}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {post.platform_posts.map((pp) => (
            <PlatformPostBadge key={pp.id} pp={pp} />
          ))}
        </div>
      </div>
    </Card>
  )
}

function PlatformPostBadge({ pp }: { pp: PlatformPost }) {
  return (
    <div className="flex items-center gap-1 text-[11px]">
      <PlatformIcon platform={pp.platform} className="h-3 w-3" />
      <span className="sr-only">{platformLabel(pp.platform)}</span>
      <StatusIcon status={pp.status} />
    </div>
  )
}

function StatusIcon({ status }: { status: PlatformPost["status"] }) {
  if (status === "succeeded") {
    return <CheckCircle2 className="h-3.5 w-3.5 text-[oklch(0.62_0.17_142)]" />
  }
  if (status === "failed" || status === "permanently_failed") {
    return <XCircle className="h-3.5 w-3.5 text-destructive" />
  }
  if (status === "cancelled") {
    return <Ban className="h-3.5 w-3.5 text-muted-foreground" />
  }
  if (status === "scheduled") {
    return <Clock className="h-3.5 w-3.5 text-muted-foreground" />
  }
  return <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
}

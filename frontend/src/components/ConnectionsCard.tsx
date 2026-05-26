import { Plug, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { PlatformIcon } from "@/components/PlatformIcon"
import type { Connections } from "@/lib/types"

interface Props {
  connections: Connections | null
  onConnectLinkedIn: () => void
}

export function ConnectionsCard({ connections, onConnectLinkedIn }: Props) {
  if (!connections) {
    return (
      <Card className="p-3 text-sm text-muted-foreground">
        Загружаем подключения…
      </Card>
    )
  }

  return (
    <Card className="p-3 flex flex-col gap-2">
      <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
        Подключения
      </div>

      <Row
        icon={<PlatformIcon platform="telegram" />}
        title="Telegram"
        subtitle={connections.telegram.channel_id ?? "не настроено"}
        ok={connections.telegram.configured && connections.telegram.healthy}
        action={null}
      />

      <Row
        icon={<PlatformIcon platform="linkedin" />}
        title="LinkedIn"
        subtitle={
          connections.linkedin.connected
            ? connections.linkedin.member_name ?? "подключено"
            : "Stage 2 — подключение скоро"
        }
        ok={connections.linkedin.connected}
        action={
          !connections.linkedin.connected ? (
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={onConnectLinkedIn}
              disabled
              title="Будет доступно в Stage 2"
            >
              <Plug className="h-3 w-3 mr-1" />
              Подключить
            </Button>
          ) : null
        }
      />
    </Card>
  )
}

function Row({
  icon,
  title,
  subtitle,
  ok,
  action,
}: {
  icon: React.ReactNode
  title: string
  subtitle: string
  ok: boolean
  action: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-2.5">
        {icon}
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-medium flex items-center gap-1.5">
            {title}
            {ok ? (
              <span className="text-[10px] uppercase tracking-wide text-[oklch(0.62_0.17_142)]">
                ok
              </span>
            ) : (
              <AlertCircle className="h-3 w-3 text-muted-foreground" />
            )}
          </span>
          <span className="text-xs text-muted-foreground">{subtitle}</span>
        </div>
      </div>
      {action}
    </div>
  )
}

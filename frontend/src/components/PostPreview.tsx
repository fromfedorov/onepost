import { Card } from "@/components/ui/card"
import { PlatformIcon, platformLabel } from "@/components/PlatformIcon"

const PLACEHOLDER = "Здесь появится текст поста…"

interface Props {
  baseText: string
  telegramText: string
  linkedinText: string
}

export function PostPreview({ baseText, telegramText, linkedinText }: Props) {
  const linkedin = (linkedinText || baseText).trim()
  const telegram = (telegramText || baseText).trim()

  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-muted-foreground mb-2">
        Предпросмотр
      </div>
      <div className="grid grid-cols-2 gap-3">
        <LinkedInPreview text={linkedin} />
        <TelegramPreview text={telegram} />
      </div>
    </div>
  )
}

function LinkedInPreview({ text }: { text: string }) {
  return (
    <Card className="p-3 flex flex-col gap-2 min-h-[180px]">
      <div className="flex items-center gap-1.5 text-xs">
        <PlatformIcon platform="linkedin" className="h-3.5 w-3.5 text-[#0a66c2]" />
        <span className="font-medium">{platformLabel("linkedin")}</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="h-7 w-7 rounded-full bg-muted-foreground/20 flex items-center justify-center text-[10px] font-semibold">
          ФС
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-xs font-medium">Ваше имя</span>
          <span className="text-[10px] text-muted-foreground">Сейчас</span>
        </div>
      </div>
      <p className={`text-[13px] whitespace-pre-wrap leading-snug ${text ? "" : "text-muted-foreground italic"}`}>
        {text || PLACEHOLDER}
      </p>
    </Card>
  )
}

function TelegramPreview({ text }: { text: string }) {
  return (
    <Card className="p-3 flex flex-col gap-2 min-h-[180px]">
      <div className="flex items-center gap-1.5 text-xs">
        <PlatformIcon platform="telegram" className="h-3.5 w-3.5 text-[#229ed9]" />
        <span className="font-medium">{platformLabel("telegram")}</span>
      </div>
      <div className="rounded-2xl bg-muted px-3 py-2 self-start max-w-full">
        <p className={`text-[13px] whitespace-pre-wrap leading-snug ${text ? "" : "text-muted-foreground italic"}`}>
          {text || PLACEHOLDER}
        </p>
      </div>
    </Card>
  )
}

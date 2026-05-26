import { useRef } from "react"
import { Image as ImageIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScheduleSheet } from "@/components/ScheduleSheet"

const MAX_COUNTER = 3000

interface Props {
  text: string
  onTextChange: (value: string) => void
  image: File | null
  onImageChange: (file: File | null) => void
  scheduledAt: Date | null
  onScheduledAtChange: (value: Date | null) => void
}

export function PostComposer({
  text,
  onTextChange,
  image,
  onImageChange,
  scheduledAt,
  onScheduledAtChange,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  function openFilePicker() {
    fileInputRef.current?.click()
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null
    onImageChange(file)
  }

  return (
    <div className="flex flex-col gap-2">
      <Textarea
        value={text}
        onChange={(e) => onTextChange(e.target.value)}
        placeholder="О чём расскажешь сегодня?"
        rows={6}
        className="min-h-[120px] resize-none"
      />
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={openFilePicker} className="gap-1.5">
            <ImageIcon className="h-3.5 w-3.5" />
            {image ? image.name.slice(0, 20) : "Изображение"}
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={handleFileChange}
          />
          {image && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onImageChange(null)}
              className="text-xs h-7"
            >
              Убрать
            </Button>
          )}
          <ScheduleSheet value={scheduledAt} onChange={onScheduledAtChange} />
        </div>
        <span className="text-xs text-muted-foreground">
          {text.length} / {MAX_COUNTER}
        </span>
      </div>
    </div>
  )
}

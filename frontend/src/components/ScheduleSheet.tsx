import { useState } from "react"
import { Clock, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { Label } from "@/components/ui/label"

interface Props {
  value: Date | null
  onChange: (next: Date | null) => void
}

function toLocalInputValue(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0")
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  )
}

export function ScheduleSheet({ value, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<string>(
    value ? toLocalInputValue(value) : ""
  )

  function handleSave() {
    if (!draft) {
      onChange(null)
    } else {
      const parsed = new Date(draft)
      if (!isNaN(parsed.getTime())) onChange(parsed)
    }
    setOpen(false)
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1.5">
          <Clock className="h-3.5 w-3.5" />
          {value ? value.toLocaleString() : "Отложить"}
          {value && (
            <X
              className="h-3.5 w-3.5 ml-1 text-muted-foreground hover:text-foreground"
              onClick={(e) => {
                e.stopPropagation()
                onChange(null)
              }}
            />
          )}
        </Button>
      </SheetTrigger>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>Запланировать публикацию</SheetTitle>
          <SheetDescription>
            Пост уйдёт автоматически в указанное время. Можно отменить из истории.
          </SheetDescription>
        </SheetHeader>
        <div className="mt-6 flex flex-col gap-3">
          <Label htmlFor="scheduled-at">Дата и время (местное)</Label>
          <input
            id="scheduled-at"
            type="datetime-local"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
          <div className="flex gap-2 mt-2">
            <Button onClick={handleSave}>Сохранить</Button>
            <Button
              variant="ghost"
              onClick={() => {
                setDraft("")
                onChange(null)
                setOpen(false)
              }}
            >
              Сбросить
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}

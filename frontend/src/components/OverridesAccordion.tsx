import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"

interface Props {
  telegramOverride: string
  linkedinOverride: string
  onTelegramChange: (value: string) => void
  onLinkedinChange: (value: string) => void
}

export function OverridesAccordion({
  telegramOverride,
  linkedinOverride,
  onTelegramChange,
  onLinkedinChange,
}: Props) {
  return (
    <Accordion type="multiple" className="w-full border-t border-border">
      <AccordionItem value="telegram">
        <AccordionTrigger>Текст для Telegram (опционально)</AccordionTrigger>
        <AccordionContent>
          <Label className="text-xs text-muted-foreground mb-1.5 block">
            Переопределит общий текст только для Telegram.
          </Label>
          <Textarea
            placeholder="Оставьте пустым, чтобы использовать общий текст"
            value={telegramOverride}
            onChange={(e) => onTelegramChange(e.target.value)}
            className="min-h-[80px] resize-none"
          />
        </AccordionContent>
      </AccordionItem>
      <AccordionItem value="linkedin">
        <AccordionTrigger>Текст для LinkedIn (опционально)</AccordionTrigger>
        <AccordionContent>
          <Label className="text-xs text-muted-foreground mb-1.5 block">
            Переопределит общий текст только для LinkedIn.
          </Label>
          <Textarea
            placeholder="Оставьте пустым, чтобы использовать общий текст"
            value={linkedinOverride}
            onChange={(e) => onLinkedinChange(e.target.value)}
            className="min-h-[80px] resize-none"
          />
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}

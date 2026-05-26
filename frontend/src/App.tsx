import { useCallback, useEffect, useRef, useState } from "react"
import { Radio } from "lucide-react"
import { Button } from "@/components/ui/button"
import { PostComposer } from "@/components/PostComposer"
import { PlatformToggle } from "@/components/PlatformToggle"
import { PostPreview } from "@/components/PostPreview"
import { OverridesAccordion } from "@/components/OverridesAccordion"
import { PublishStatus } from "@/components/PublishStatus"
import { ConnectionsCard } from "@/components/ConnectionsCard"
import { History } from "@/components/History"
import { ThemeToggle } from "@/components/ThemeToggle"
import { api } from "@/lib/api"
import type { Connections, Platform, Post } from "@/lib/types"

const ACTIVE_STATUSES = new Set(["queued", "publishing", "scheduled"])

function isPostSettled(post: Post | null): boolean {
  if (!post) return true
  return !post.platform_posts.some((pp) => ACTIVE_STATUSES.has(pp.status))
}

function App() {
  const [text, setText] = useState("")
  const [image, setImage] = useState<File | null>(null)
  const [telegramEnabled, setTelegramEnabled] = useState(true)
  const [linkedinEnabled, setLinkedinEnabled] = useState(true)
  const [telegramOverride, setTelegramOverride] = useState("")
  const [linkedinOverride, setLinkedinOverride] = useState("")
  const [scheduledAt, setScheduledAt] = useState<Date | null>(null)
  const [publishing, setPublishing] = useState(false)
  const [currentPost, setCurrentPost] = useState<Post | null>(null)
  const [history, setHistory] = useState<Post[]>([])
  const [connections, setConnections] = useState<Connections | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const refreshHistory = useCallback(async () => {
    try {
      const posts = await api.listPosts()
      setHistory(posts)
    } catch (err) {
      console.error("failed to load history", err)
    }
  }, [])

  const refreshConnections = useCallback(async () => {
    try {
      setConnections(await api.getConnections())
    } catch (err) {
      console.error("failed to load connections", err)
    }
  }, [])

  useEffect(() => {
    void refreshHistory()
    void refreshConnections()
  }, [refreshHistory, refreshConnections])

  const pollTimerRef = useRef<number | null>(null)
  useEffect(() => {
    if (!currentPost || isPostSettled(currentPost)) {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
      return
    }
    const id = currentPost.id
    pollTimerRef.current = window.setInterval(async () => {
      try {
        const fresh = await api.getPost(id)
        setCurrentPost(fresh)
        if (isPostSettled(fresh)) {
          void refreshHistory()
        }
      } catch (err) {
        console.error("poll failed", err)
      }
    }, 1500)
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
    }
  }, [currentPost, refreshHistory])

  const selectedPlatforms: Platform[] = []
  if (telegramEnabled) selectedPlatforms.push("telegram")
  if (linkedinEnabled) selectedPlatforms.push("linkedin")

  const canSubmit =
    text.trim().length > 0 && selectedPlatforms.length > 0 && !publishing

  async function handlePublish() {
    if (!canSubmit) return
    setSubmitError(null)
    setPublishing(true)
    try {
      const post = await api.createPost({
        text: text.trim(),
        image,
        platforms: selectedPlatforms,
        textOverrideTelegram: telegramOverride.trim() || undefined,
        textOverrideLinkedIn: linkedinOverride.trim() || undefined,
        scheduledAt,
      })
      setCurrentPost(post)
      setText("")
      setImage(null)
      setTelegramOverride("")
      setLinkedinOverride("")
      setScheduledAt(null)
      void refreshHistory()
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось опубликовать"
      setSubmitError(message)
    } finally {
      setPublishing(false)
    }
  }

  async function handleRetry(platform: Platform) {
    if (!currentPost) return
    try {
      await api.retryPlatform(currentPost.id, platform)
      const fresh = await api.getPost(currentPost.id)
      setCurrentPost(fresh)
    } catch (err) {
      console.error("retry failed", err)
    }
  }

  async function handleCancel(postId: string) {
    try {
      await api.cancelPost(postId)
      await refreshHistory()
    } catch (err) {
      console.error("cancel failed", err)
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-[560px] px-4 py-6 flex flex-col gap-5">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Radio className="h-5 w-5" />
            <span className="font-semibold">OnePost</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Новый пост</span>
            <ThemeToggle />
          </div>
        </header>

        <ConnectionsCard
          connections={connections}
          onConnectLinkedIn={() => {
            // Stage 2: window.location.assign("/api/oauth/linkedin/start")
          }}
        />

        <PostComposer
          text={text}
          onTextChange={setText}
          image={image}
          onImageChange={setImage}
          scheduledAt={scheduledAt}
          onScheduledAtChange={setScheduledAt}
        />

        <OverridesAccordion
          telegramOverride={telegramOverride}
          linkedinOverride={linkedinOverride}
          onTelegramChange={setTelegramOverride}
          onLinkedinChange={setLinkedinOverride}
        />

        <section className="flex flex-col gap-2">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            Публиковать в
          </div>
          <PlatformToggle
            platform="linkedin"
            caption="личный профиль"
            enabled={linkedinEnabled}
            onChange={setLinkedinEnabled}
          />
          <PlatformToggle
            platform="telegram"
            caption={connections?.telegram.channel_id ?? "@my_channel"}
            enabled={telegramEnabled}
            onChange={setTelegramEnabled}
          />
        </section>

        <PostPreview
          baseText={text}
          telegramText={telegramOverride}
          linkedinText={linkedinOverride}
        />

        <Button
          className="w-full"
          size="lg"
          disabled={!canSubmit}
          onClick={handlePublish}
        >
          {publishing
            ? "Отправляем…"
            : scheduledAt
              ? "Запланировать"
              : "Опубликовать в оба"}
        </Button>

        {submitError && (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {submitError}
          </div>
        )}

        {currentPost && (
          <PublishStatus
            platformPosts={currentPost.platform_posts}
            onRetry={handleRetry}
          />
        )}

        <History posts={history} onCancel={handleCancel} />
      </div>
    </div>
  )
}

export default App

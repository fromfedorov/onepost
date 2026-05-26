import type {
  Connections,
  CreatePostInput,
  OnepostApi,
  Platform,
  PlatformPost,
  PlatformPostStatus,
  Post,
} from "./types"

type Outcome = "success" | "transient" | "permanent"

const SETTINGS = {
  delayMs: 1200,
  outcome: "success" as Outcome,
}

export const mockControls = {
  setDelay(ms: number) {
    SETTINGS.delayMs = ms
  },
  setOutcome(outcome: Outcome) {
    SETTINGS.outcome = outcome
  },
}

function uuid(): string {
  return crypto.randomUUID()
}

function nowIso(): string {
  return new Date().toISOString()
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

const store = {
  posts: new Map<string, Post>(),
}

function buildPlatformPost(platform: Platform, post: Post): PlatformPost {
  return {
    id: uuid(),
    platform,
    status: post.scheduled_at ? "scheduled" : "queued",
    text_override: null,
    external_id: null,
    external_url: null,
    attempts: 0,
    next_attempt_at: null,
    last_error: null,
    updated_at: nowIso(),
  }
}

async function simulatePublish(pp: PlatformPost): Promise<void> {
  pp.status = "publishing"
  pp.updated_at = nowIso()
  pp.attempts += 1
  await sleep(SETTINGS.delayMs)

  switch (SETTINGS.outcome) {
    case "success":
      pp.status = "succeeded"
      pp.external_id = String(Math.floor(Math.random() * 100000))
      pp.external_url =
        pp.platform === "telegram"
          ? `https://t.me/c/mock/${pp.external_id}`
          : `https://www.linkedin.com/feed/update/urn:li:share:${pp.external_id}`
      pp.last_error = null
      break
    case "transient":
      pp.status = "failed"
      pp.last_error = "Имитация: 429 Too Many Requests"
      break
    case "permanent":
      pp.status = "permanently_failed"
      pp.last_error = "Имитация: 401 Unauthorized (нужна реавторизация)"
      break
  }
  pp.updated_at = nowIso()
}

export const mockApi: OnepostApi = {
  async listPosts(): Promise<Post[]> {
    return Array.from(store.posts.values()).sort((a, b) =>
      b.created_at.localeCompare(a.created_at)
    )
  },

  async getPost(id: string): Promise<Post> {
    const p = store.posts.get(id)
    if (!p) throw new Error("Post not found")
    return p
  },

  async createPost(input: CreatePostInput): Promise<Post> {
    await sleep(150)
    const post: Post = {
      id: uuid(),
      content: input.text,
      state: input.scheduledAt ? "scheduled" : "publishing",
      scheduled_at: input.scheduledAt ? input.scheduledAt.toISOString() : null,
      created_at: nowIso(),
      image: null,
      platform_posts: [],
    }
    post.platform_posts = input.platforms.map((p) => {
      const pp = buildPlatformPost(p, post)
      pp.text_override =
        p === "telegram"
          ? input.textOverrideTelegram ?? null
          : input.textOverrideLinkedIn ?? null
      return pp
    })
    store.posts.set(post.id, post)

    if (!input.scheduledAt) {
      void (async () => {
        await Promise.all(post.platform_posts.map(simulatePublish))
        post.state = post.platform_posts.every((pp) => pp.status === "succeeded")
          ? "done"
          : "failed"
      })()
    }
    return post
  },

  async retryPlatform(postId: string, platform: Platform): Promise<void> {
    const post = store.posts.get(postId)
    if (!post) throw new Error("Post not found")
    const pp = post.platform_posts.find((p) => p.platform === platform)
    if (!pp) throw new Error("Platform post not found")
    pp.attempts = 0
    pp.next_attempt_at = null
    pp.last_error = null
    pp.status = "queued"
    void simulatePublish(pp)
  },

  async cancelPost(postId: string): Promise<void> {
    const post = store.posts.get(postId)
    if (!post) throw new Error("Post not found")
    for (const pp of post.platform_posts) {
      if (pp.status === "scheduled") {
        pp.status = "cancelled" as PlatformPostStatus
      }
    }
    post.state = "failed"
  },

  async getConnections(): Promise<Connections> {
    return {
      telegram: {
        configured: true,
        healthy: true,
        channel_id: "@my_channel",
      },
      linkedin: {
        configured: false,
        connected: false,
        member_name: null,
        refresh_expires_at: null,
      },
    }
  },
}

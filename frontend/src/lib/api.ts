import type {
  Connections,
  CreatePostInput,
  OnepostApi,
  Platform,
  Post,
} from "./types"

const BASE = "/api"

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.headers ?? {}),
    },
  })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = body.detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }
  if (res.status === 204) return undefined as unknown as T
  return (await res.json()) as T
}

export const realApi: OnepostApi = {
  async listPosts() {
    const data = await jsonFetch<{ posts: Post[] }>("/posts")
    return data.posts
  },

  async getPost(id) {
    return await jsonFetch<Post>(`/posts/${id}`)
  },

  async createPost(input: CreatePostInput) {
    const form = new FormData()
    form.set("text", input.text)
    form.set("platforms", input.platforms.join(","))
    if (input.image) form.set("image", input.image)
    if (input.textOverrideTelegram) form.set("text_override_telegram", input.textOverrideTelegram)
    if (input.textOverrideLinkedIn) form.set("text_override_linkedin", input.textOverrideLinkedIn)
    if (input.scheduledAt) form.set("scheduled_at", input.scheduledAt.toISOString())
    const res = await fetch(`${BASE}/posts`, { method: "POST", body: form })
    if (!res.ok) {
      let detail = `HTTP ${res.status}`
      try {
        const body = await res.json()
        if (body?.detail) detail = body.detail
      } catch {
        // ignore
      }
      throw new Error(detail)
    }
    return (await res.json()) as Post
  },

  async retryPlatform(postId, platform: Platform) {
    await jsonFetch<void>(`/posts/${postId}/retry/${platform}`, { method: "POST" })
  },

  async cancelPost(postId) {
    await jsonFetch<void>(`/posts/${postId}`, { method: "DELETE" })
  },

  async getConnections() {
    return await jsonFetch<Connections>("/connections")
  },
}

export const api: OnepostApi = realApi

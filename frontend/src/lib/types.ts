export type Platform = "telegram" | "linkedin"

export type PlatformPostStatus =
  | "pending"
  | "scheduled"
  | "queued"
  | "publishing"
  | "succeeded"
  | "failed"
  | "permanently_failed"
  | "cancelled"

export type PostState = "draft" | "scheduled" | "publishing" | "done" | "failed"

export interface Media {
  id: string
  mime_type: string
  size_bytes: number
}

export interface PlatformPost {
  id: string
  platform: Platform
  status: PlatformPostStatus
  text_override: string | null
  external_id: string | null
  external_url: string | null
  attempts: number
  next_attempt_at: string | null
  last_error: string | null
  updated_at: string
}

export interface Post {
  id: string
  content: string
  state: PostState
  scheduled_at: string | null
  created_at: string
  image: Media | null
  platform_posts: PlatformPost[]
}

export interface TelegramConnection {
  configured: boolean
  healthy: boolean
  channel_id: string | null
}

export interface LinkedInConnection {
  configured: boolean
  connected: boolean
  member_name: string | null
  refresh_expires_at: string | null
}

export interface Connections {
  telegram: TelegramConnection
  linkedin: LinkedInConnection
}

export interface CreatePostInput {
  text: string
  image: File | null
  platforms: Platform[]
  textOverrideTelegram?: string
  textOverrideLinkedIn?: string
  scheduledAt?: Date | null
}

export interface OnepostApi {
  listPosts(): Promise<Post[]>
  getPost(id: string): Promise<Post>
  createPost(input: CreatePostInput): Promise<Post>
  retryPlatform(postId: string, platform: Platform): Promise<void>
  cancelPost(postId: string): Promise<void>
  getConnections(): Promise<Connections>
}

export type LanguageCode = 'auto' | 'zh' | 'en' | 'ja' | 'ko' | 'de' | 'fr'
export type SupportedLanguageCode = Exclude<LanguageCode, 'auto'>
export type HistoryType = 'text' | 'file'
export type HistoryFilter = 'all' | HistoryType
export type TextHistoryStatus = 'success' | 'failed'
export type FileTaskStatus =
  | 'pending'
  | 'hashing'
  | 'uploading'
  | 'queued'
  | 'translating'
  | 'done'
  | 'failed'
  | 'cancelled'

export type HistoryStatus = TextHistoryStatus | FileTaskStatus

export type LanguageOption = {
  code: SupportedLanguageCode
  label: string
}

export type UserInfo = {
  userId: string
  name: string
  avatar?: string
  email?: string
}

export type AuthTokens = {
  accessToken: string
  refreshToken: string
  expiresAt: number
}

export type HistoryItem = {
  id: string
  taskType: HistoryType
  title: string
  status: HistoryStatus
  sourceLang: string
  targetLang: string
  updatedAt: string
  resultPreview?: string
  sourceText?: string
  translatedText?: string
  fileId?: string
  taskId?: string
  resultFileId?: string
  bilingualFileId?: string
}

export type FileTask = {
  localId: string
  file: File | null
  name: string
  size: number
  status: FileTaskStatus
  uploadProgress: number
  fileId?: string
  taskId?: string
  historyId?: string
  resultFileId?: string
  bilingualFileId?: string
  sourceLang: LanguageCode
  targetLang: SupportedLanguageCode
  error?: string
}

export type ApiEnvelope<T> = {
  data: T
}

export type PaginationResult<T> = {
  items: T[]
  total: number
  page: number
  pageSize: number
}

export type TextTranslateResult = {
  taskId: string
  translatedText: string
  sourceLang: SupportedLanguageCode
  terminologyCount: number
  historyId: string
}

export type FileTranslateResult = {
  taskId: string
  status: FileTaskStatus
  historyId: string
}

export type FileTaskStatusResult = {
  taskId: string
  status: FileTaskStatus
  resultFileId?: string
  bilingualFileId?: string
  updatedAt: string
  error?: string
}

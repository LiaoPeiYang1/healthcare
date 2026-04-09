import { request } from '@/api/client'
import type {
  ApiEnvelope,
  FileTaskStatusResult,
  FileTranslateResult,
  LanguageCode,
  SupportedLanguageCode,
  TextTranslateResult,
} from '@/types'

type RawTextTranslate = {
  task_id: string
  translated_text: string
  source_lang: SupportedLanguageCode
  terminology_count: number
  history_id: string
}

type RawFileTranslate = {
  task_id: string
  status: FileTranslateResult['status']
  history_id: string
}

type RawTaskStatus = {
  task_id: string
  status: FileTaskStatusResult['status']
  result_file_id?: string
  bilingual_file_id?: string
  updated_at: string
  error?: string
}

export async function detectSourceLanguage(text: string) {
  const response = await request<ApiEnvelope<{ lang: SupportedLanguageCode; confidence: number }>>('/api/detect', {
    method: 'POST',
    body: JSON.stringify({ text }),
  })
  return response.data
}

export async function translateText(payload: {
  text: string
  sourceLang: LanguageCode
  targetLang: SupportedLanguageCode
  historyId?: string
}) {
  const response = await request<ApiEnvelope<RawTextTranslate>>('/api/translate/text', {
    method: 'POST',
    body: JSON.stringify({
      text: payload.text,
      source_lang: payload.sourceLang,
      target_lang: payload.targetLang,
      history_id: payload.historyId,
    }),
  })

  return {
    taskId: response.data.task_id,
    translatedText: response.data.translated_text,
    sourceLang: response.data.source_lang,
    terminologyCount: response.data.terminology_count,
    historyId: response.data.history_id,
  } as TextTranslateResult
}

export async function submitFileTranslation(payload: {
  fileId: string
  sourceLang: LanguageCode
  targetLang: SupportedLanguageCode
  historyId?: string
}) {
  const response = await request<ApiEnvelope<RawFileTranslate>>('/api/translate/file', {
    method: 'POST',
    body: JSON.stringify({
      file_id: payload.fileId,
      source_lang: payload.sourceLang,
      target_lang: payload.targetLang,
      history_id: payload.historyId,
    }),
  })

  return {
    taskId: response.data.task_id,
    status: response.data.status,
    historyId: response.data.history_id,
  } as FileTranslateResult
}

export async function getFileTaskStatus(taskId: string) {
  const response = await request<ApiEnvelope<RawTaskStatus>>(`/api/translate/status/${taskId}`)
  return {
    taskId: response.data.task_id,
    status: response.data.status,
    resultFileId: response.data.result_file_id,
    bilingualFileId: response.data.bilingual_file_id,
    updatedAt: response.data.updated_at,
    error: response.data.error,
  } as FileTaskStatusResult
}

export async function cancelFileTranslation(taskId: string) {
  const response = await request<ApiEnvelope<{ task_id: string; status: FileTaskStatusResult['status'] }>>(
    `/api/translate/cancel/${taskId}`,
    {
      method: 'POST',
    },
  )
  return {
    taskId: response.data.task_id,
    status: response.data.status,
  }
}

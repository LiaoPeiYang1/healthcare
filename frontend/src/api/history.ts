import { request } from '@/api/client'
import type { ApiEnvelope, HistoryFilter, HistoryItem, PaginationResult } from '@/types'

type RawHistoryItem = {
  id: string
  task_type: 'text' | 'file'
  title: string
  status: string
  source_lang: string
  target_lang: string
  updated_at: string
  result_preview?: string
  source_text?: string
  translated_text?: string
  file_id?: string
  task_id?: string
  result_file_id?: string
  bilingual_file_id?: string
}

type RawHistoryPage = {
  items: RawHistoryItem[]
  total: number
  page: number
  page_size: number
}

function normalizeHistoryItem(item: RawHistoryItem): HistoryItem {
  return {
    id: item.id,
    taskType: item.task_type,
    title: item.title,
    status: item.status as HistoryItem['status'],
    sourceLang: item.source_lang,
    targetLang: item.target_lang,
    updatedAt: item.updated_at,
    resultPreview: item.result_preview,
    sourceText: item.source_text,
    translatedText: item.translated_text ?? item.result_preview,
    fileId: item.file_id,
    taskId: item.task_id,
    resultFileId: item.result_file_id,
    bilingualFileId: item.bilingual_file_id,
  }
}

export async function listHistory(params: {
  page: number
  pageSize: number
  filter: HistoryFilter
  keyword: string
}) {
  const search = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  })
  if (params.filter !== 'all') search.set('task_type', params.filter)
  if (params.keyword.trim()) search.set('keyword', params.keyword.trim())

  const response = await request<ApiEnvelope<RawHistoryPage>>(`/api/history?${search.toString()}`)
  return {
    items: response.data.items.map(normalizeHistoryItem),
    total: response.data.total,
    page: response.data.page,
    pageSize: response.data.page_size,
  } as PaginationResult<HistoryItem>
}

export async function getHistoryDetail(historyId: string) {
  const response = await request<ApiEnvelope<RawHistoryItem>>(`/api/history/${historyId}`)
  return normalizeHistoryItem(response.data)
}

export async function deleteHistoryItem(historyId: string) {
  await request<void>(`/api/history/${historyId}`, {
    method: 'DELETE',
    parseAs: 'void',
  })
}

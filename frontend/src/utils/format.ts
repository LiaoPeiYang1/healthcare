import { format } from 'date-fns'

import type { FileTaskStatus, LanguageOption, SupportedLanguageCode } from '@/types'

export const supportedLanguages: LanguageOption[] = [
  { code: 'zh', label: '中文' },
  { code: 'en', label: '英文' },
  { code: 'ja', label: '日文' },
  { code: 'ko', label: '韩文' },
  { code: 'de', label: '德文' },
  { code: 'fr', label: '法文' },
]

const languageMap = new Map(supportedLanguages.map((item) => [item.code, item.label]))

export function formatLanguage(codeOrLabel: string) {
  return languageMap.get(codeOrLabel as SupportedLanguageCode) ?? codeOrLabel
}

export function formatFileSize(bytes: number) {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${bytes} B`
}

export function statusLabel(status: FileTaskStatus | string) {
  const labels: Record<string, string> = {
    pending: '待处理',
    hashing: '计算文件指纹中',
    uploading: '上传中',
    queued: '排队中',
    translating: '翻译中',
    done: '已完成',
    failed: '失败',
    cancelled: '已取消',
    success: '成功',
  }
  return labels[status] ?? status
}

export function isActiveFileStatus(status?: string) {
  return ['pending', 'hashing', 'uploading', 'queued', 'translating'].includes(status ?? '')
}

export function todayStamp() {
  return format(new Date(), 'yyyyMMdd')
}

export function buildDownloadFilename(title: string, targetLang: string) {
  const sanitized = title.replace(/\.[^.]+$/, '')
  return `${sanitized}_${targetLang}_${todayStamp()}.pdf`
}

export function formatHistoryDate(value: string) {
  const normalized = value.includes('T') ? value : value.replace(' ', 'T')
  const parsed = new Date(normalized)
  if (Number.isNaN(parsed.getTime())) return value
  return format(parsed, 'yyyy/M/d')
}

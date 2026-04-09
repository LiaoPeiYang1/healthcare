import { create } from 'zustand'

import type { HistoryItem, LanguageCode, SupportedLanguageCode } from '@/types'

type TranslateState = {
  currentHistoryId: string | null
  sourceText: string
  translatedText: string
  sourceLang: LanguageCode
  targetLang: SupportedLanguageCode
  detectedLang: SupportedLanguageCode | null
  status: 'idle' | 'loading' | 'success' | 'failed'
  error: string | null
  setLanguages: (sourceLang: LanguageCode, targetLang: SupportedLanguageCode) => void
  setSourceText: (text: string) => void
  setDetectedLang: (lang: SupportedLanguageCode | null) => void
  setPending: () => void
  setResult: (payload: {
    historyId: string
    sourceText: string
    translatedText: string
    sourceLang: SupportedLanguageCode
    targetLang: SupportedLanguageCode
  }) => void
  setFailure: (payload: {
    historyId?: string
    sourceText: string
    sourceLang: LanguageCode
    targetLang: SupportedLanguageCode
    error: string
  }) => void
  hydrateFromHistory: (item: HistoryItem) => void
  reset: () => void
}

export const useTranslateStore = create<TranslateState>((set) => ({
  currentHistoryId: null,
  sourceText: '',
  translatedText: '',
  sourceLang: 'auto',
  targetLang: 'en',
  detectedLang: null,
  status: 'idle',
  error: null,
  setLanguages(sourceLang, targetLang) {
    set({ sourceLang, targetLang })
  },
  setSourceText(sourceText) {
    set({ sourceText })
  },
  setDetectedLang(detectedLang) {
    set({ detectedLang })
  },
  setPending() {
    set({ status: 'loading', error: null })
  },
  setResult(payload) {
    set({
      currentHistoryId: payload.historyId,
      sourceText: payload.sourceText,
      translatedText: payload.translatedText,
      sourceLang: payload.sourceLang,
      targetLang: payload.targetLang,
      detectedLang: payload.sourceLang,
      status: 'success',
      error: null,
    })
  },
  setFailure(payload) {
    set({
      currentHistoryId: payload.historyId ?? null,
      sourceText: payload.sourceText,
      sourceLang: payload.sourceLang,
      targetLang: payload.targetLang,
      translatedText: payload.error,
      status: 'failed',
      error: payload.error,
    })
  },
  hydrateFromHistory(item) {
    set({
      currentHistoryId: item.id,
      sourceText: item.sourceText ?? '',
      translatedText: item.translatedText ?? item.resultPreview ?? '',
      sourceLang: item.sourceLang as LanguageCode,
      targetLang: item.targetLang as SupportedLanguageCode,
      detectedLang: item.sourceLang as SupportedLanguageCode,
      status: item.status === 'failed' ? 'failed' : 'success',
      error: item.status === 'failed' ? item.resultPreview ?? '翻译失败，请重试' : null,
    })
  },
  reset() {
    set({
      currentHistoryId: null,
      sourceText: '',
      translatedText: '',
      sourceLang: 'auto',
      targetLang: 'en',
      detectedLang: null,
      status: 'idle',
      error: null,
    })
  },
}))

import { useCallback, useEffect, useMemo } from 'react'

import { detectSourceLanguage, translateText } from '@/api/translate'
import { useHistoryStore } from '@/store/history'
import { useTranslateStore } from '@/store/translate'
import type { HistoryItem, SupportedLanguageCode } from '@/types'

function nowLabel() {
  return new Date().toLocaleString('zh-CN', { hour12: false })
}

export function useTextTranslation() {
  const {
    currentHistoryId,
    sourceText,
    translatedText,
    sourceLang,
    targetLang,
    detectedLang,
    status,
    error,
    setSourceText,
    setLanguages,
    setDetectedLang,
    setPending,
    setResult,
    setFailure,
    reset,
  } = useTranslateStore()
  const historyStore = useHistoryStore()

  useEffect(() => {
    if (sourceLang !== 'auto' || !sourceText.trim()) {
      setDetectedLang(null)
      return
    }

    const timer = window.setTimeout(async () => {
      try {
        const result = await detectSourceLanguage(sourceText.slice(0, 500))
        setDetectedLang(result.lang)
      } catch {
        setDetectedLang(null)
      }
    }, 500)

    return () => window.clearTimeout(timer)
  }, [setDetectedLang, sourceLang, sourceText])

  const resolvedSourceLang = useMemo(
    () => (sourceLang === 'auto' ? detectedLang : sourceLang),
    [detectedLang, sourceLang],
  )

  const canSubmit = Boolean(
    sourceText.trim() && resolvedSourceLang && resolvedSourceLang !== targetLang && status !== 'loading',
  )

  const submit = useCallback(async () => {
    const nextResolvedSource = sourceLang === 'auto' ? detectedLang : sourceLang
    if (!sourceText.trim()) return
    if (!nextResolvedSource) {
      setFailure({
        sourceText,
        sourceLang,
        targetLang,
        error: '暂未识别出源语言，请稍后重试',
      })
      return
    }
    if (nextResolvedSource === targetLang) {
      setFailure({
        sourceText,
        sourceLang,
        targetLang,
        error: '源语言与目标语言不能相同',
      })
      return
    }

    const currentHistory = currentHistoryId
      ? historyStore.items.find((item) => item.id === currentHistoryId && item.taskType === 'text')
      : null
    const shouldReuseHistory =
      currentHistory &&
      currentHistory.sourceLang === nextResolvedSource &&
      currentHistory.targetLang === targetLang

    setPending()

    try {
      const result = await translateText({
        text: sourceText,
        sourceLang,
        targetLang,
        historyId: shouldReuseHistory ? currentHistory?.id : undefined,
      })

      setResult({
        historyId: result.historyId,
        sourceText,
        translatedText: result.translatedText,
        sourceLang: result.sourceLang,
        targetLang,
      })

      const historyItem: HistoryItem = {
        id: result.historyId,
        taskType: 'text',
        title: sourceText.slice(0, 50),
        status: 'success',
        sourceLang: result.sourceLang,
        targetLang,
        updatedAt: nowLabel(),
        sourceText,
        translatedText: result.translatedText,
        resultPreview: result.translatedText,
      }
      historyStore.upsertItem(historyItem)
      historyStore.setSelectedId(result.historyId)
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : '翻译失败，请稍后重试'
      const failedHistoryId = shouldReuseHistory ? currentHistory?.id ?? null : currentHistoryId
      setFailure({
        historyId: failedHistoryId ?? undefined,
        sourceText,
        sourceLang,
        targetLang,
        error: message,
      })

      const historyId = failedHistoryId ?? `text-${Date.now()}`
      historyStore.upsertItem({
        id: historyId,
        taskType: 'text',
        title: sourceText.slice(0, 50),
        status: 'failed',
        sourceLang: nextResolvedSource,
        targetLang,
        updatedAt: nowLabel(),
        sourceText,
        translatedText: message,
        resultPreview: message,
      })
      historyStore.setSelectedId(historyId)
    }
  }, [
    currentHistoryId,
    detectedLang,
    historyStore,
    setFailure,
    setPending,
    setResult,
    sourceLang,
    sourceText,
    targetLang,
  ])

  const retry = useCallback(async () => {
    await submit()
  }, [submit])

  const setTargetLanguage = useCallback(
    (nextTarget: SupportedLanguageCode) => {
      setLanguages('auto', nextTarget)
    },
    [setLanguages],
  )

  return {
    sourceText,
    translatedText,
    sourceLang,
    targetLang,
    detectedLang,
    resolvedSourceLang,
    status,
    error,
    canSubmit,
    setSourceText,
    setLanguages,
    setTargetLanguage,
    submit,
    retry,
    reset,
  }
}

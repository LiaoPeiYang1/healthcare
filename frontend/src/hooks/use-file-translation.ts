import { useCallback } from 'react'

import { nanoid } from 'nanoid'
import { cancelFileTranslation, submitFileTranslation } from '@/api/translate'
import { useFileUpload } from '@/hooks/use-file-upload'
import { useFileTranslateStore } from '@/store/file-translate'
import { useHistoryStore } from '@/store/history'
import type { FileTask, HistoryItem, LanguageCode, SupportedLanguageCode } from '@/types'
import { isActiveFileStatus } from '@/utils/format'

function nowLabel() {
  return new Date().toLocaleString('zh-CN', { hour12: false })
}

export function useFileTranslation() {
  const { uploadFile } = useFileUpload()
  const { currentTask, setTask, updateTask, startPolling, clearTask } = useFileTranslateStore()
  const historyStore = useHistoryStore()

  const start = useCallback(
    async (payload: { file: File; sourceLang: LanguageCode; targetLang: SupportedLanguageCode; historyId?: string }) => {
      if (currentTask && isActiveFileStatus(currentTask.status)) {
        throw new Error('当前已有文件在处理中，请先完成或删除当前任务')
      }

      const baseTask: FileTask = {
        localId: nanoid(),
        file: payload.file,
        name: payload.file.name,
        size: payload.file.size,
        status: 'pending',
        uploadProgress: 0,
        sourceLang: payload.sourceLang,
        targetLang: payload.targetLang,
        historyId: payload.historyId,
      }
      setTask(baseTask)

      try {
        const uploaded = await uploadFile(payload.file)
        updateTask({ fileId: uploaded.fileId })

        const translated = await submitFileTranslation({
          fileId: uploaded.fileId,
          sourceLang: payload.sourceLang,
          targetLang: payload.targetLang,
          historyId: payload.historyId,
        })

        updateTask({
          fileId: uploaded.fileId,
          taskId: translated.taskId,
          historyId: translated.historyId,
          status: translated.status,
          uploadProgress: 100,
        })

        const historyItem: HistoryItem = {
          id: translated.historyId,
          taskType: 'file',
          title: payload.file.name,
          status: translated.status,
          sourceLang: payload.sourceLang,
          targetLang: payload.targetLang,
          updatedAt: nowLabel(),
          fileId: uploaded.fileId,
          taskId: translated.taskId,
        }
        historyStore.upsertItem(historyItem)
        historyStore.setSelectedId(translated.historyId)
        startPolling(translated.taskId, translated.historyId)
      } catch (error) {
        const message = error instanceof Error ? error.message : '文件处理失败'
        updateTask({ status: 'failed', error: message })
        throw error
      }
    },
    [currentTask, historyStore, setTask, startPolling, updateTask, uploadFile],
  )

  const retry = useCallback(async () => {
    if (!currentTask) return
    if (currentTask.fileId) {
      const translated = await submitFileTranslation({
        fileId: currentTask.fileId,
        sourceLang: currentTask.sourceLang,
        targetLang: currentTask.targetLang,
        historyId: currentTask.historyId,
      })
      updateTask({ taskId: translated.taskId, status: translated.status, error: undefined })
      historyStore.updateItem(translated.historyId, {
        status: translated.status,
        updatedAt: nowLabel(),
        taskId: translated.taskId,
      })
      startPolling(translated.taskId, translated.historyId)
      return
    }
    if (currentTask.file) {
      await start({
        file: currentTask.file,
        sourceLang: currentTask.sourceLang,
        targetLang: currentTask.targetLang,
        historyId: currentTask.historyId,
      })
    }
  }, [currentTask, historyStore, start, startPolling, updateTask])

  const cancel = useCallback(async () => {
    if (!currentTask?.taskId || !currentTask.historyId) return
    await cancelFileTranslation(currentTask.taskId)
    updateTask({ status: 'cancelled' })
    historyStore.updateItem(currentTask.historyId, {
      status: 'cancelled',
      updatedAt: nowLabel(),
    })
  }, [currentTask, historyStore, updateTask])

  const reset = useCallback(() => {
    clearTask()
  }, [clearTask])

  return {
    currentTask,
    start,
    retry,
    cancel,
    reset,
  }
}

import { create } from 'zustand'

import { getFileTaskStatus } from '@/api/translate'
import { useHistoryStore } from '@/store/history'
import type { FileTask, HistoryItem } from '@/types'

const pollingMap = new Map<string, number>()

type FileTranslateState = {
  currentTask: FileTask | null
  setTask: (task: FileTask) => void
  updateTask: (patch: Partial<FileTask>) => void
  hydrateFromHistory: (item: HistoryItem) => void
  clearTask: () => void
  startPolling: (taskId: string, historyId?: string) => void
  stopPolling: (taskId: string) => void
  stopAllPolling: () => void
}

export const useFileTranslateStore = create<FileTranslateState>((set, get) => ({
  currentTask: null,
  setTask(task) {
    set({ currentTask: task })
  },
  updateTask(patch) {
    set((state) => ({
      currentTask: state.currentTask ? { ...state.currentTask, ...patch } : state.currentTask,
    }))
  },
  hydrateFromHistory(item) {
    set({
      currentTask: {
        localId: item.id,
        file: null,
        name: item.title,
        size: 0,
        status: item.status as FileTask['status'],
        uploadProgress: item.status === 'done' ? 100 : 0,
        fileId: item.fileId,
        taskId: item.taskId,
        historyId: item.id,
        resultFileId: item.resultFileId,
        bilingualFileId: item.bilingualFileId,
        sourceLang: item.sourceLang as FileTask['sourceLang'],
        targetLang: item.targetLang as FileTask['targetLang'],
      },
    })
  },
  clearTask() {
    const taskId = get().currentTask?.taskId
    if (taskId) get().stopPolling(taskId)
    set({ currentTask: null })
  },
  startPolling(taskId, historyId) {
    if (pollingMap.has(taskId)) return

    const timer = window.setInterval(async () => {
      try {
        const result = await getFileTaskStatus(taskId)
        const nextPatch: Partial<FileTask> = {
          status: result.status,
          resultFileId: result.resultFileId,
          bilingualFileId: result.bilingualFileId,
          error: result.error,
        }

        if (get().currentTask?.taskId === taskId) {
          get().updateTask(nextPatch)
        }

        const historyStore = useHistoryStore.getState()
        if (historyId) {
          historyStore.updateItem(historyId, {
            status: result.status,
            updatedAt: result.updatedAt,
            resultFileId: result.resultFileId,
            bilingualFileId: result.bilingualFileId,
          })
        } else {
          historyStore.updateByTaskId(taskId, {
            status: result.status,
            updatedAt: result.updatedAt,
            resultFileId: result.resultFileId,
            bilingualFileId: result.bilingualFileId,
          })
        }

        if (['done', 'failed', 'cancelled'].includes(result.status)) {
          get().stopPolling(taskId)
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : '任务状态获取失败'
        get().updateTask({ status: 'failed', error: message })
        useHistoryStore.getState().updateByTaskId(taskId, {
          status: 'failed',
          updatedAt: new Date().toLocaleString('zh-CN', { hour12: false }),
        })
        get().stopPolling(taskId)
      }
    }, 2000)

    pollingMap.set(taskId, timer)
  },
  stopPolling(taskId) {
    const timer = pollingMap.get(taskId)
    if (timer) {
      window.clearInterval(timer)
      pollingMap.delete(taskId)
    }
  },
  stopAllPolling() {
    pollingMap.forEach((timer) => window.clearInterval(timer))
    pollingMap.clear()
  },
}))

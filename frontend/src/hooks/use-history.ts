import { useCallback, useEffect } from 'react'

import { deleteHistoryItem, getHistoryDetail, listHistory } from '@/api/history'
import { useFileTranslateStore } from '@/store/file-translate'
import { useHistoryStore } from '@/store/history'
import { useTranslateStore } from '@/store/translate'
import type { HistoryItem } from '@/types'
import { isActiveFileStatus } from '@/utils/format'

export function useHistory() {
  const {
    items,
    loading,
    selectedId,
    filter,
    keyword,
    page,
    pageSize,
    total,
    setLoading,
    setList,
    setFilter,
    setKeyword,
    setPage,
    setSelectedId,
    resetSelection,
    removeItem,
  } = useHistoryStore()
  const fileStore = useFileTranslateStore()
  const translateStore = useTranslateStore()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const response = await listHistory({
        page,
        pageSize,
        filter,
        keyword,
      })
      setList(response.items, response.total, response.page)
    } finally {
      setLoading(false)
    }
  }, [filter, keyword, page, pageSize, setList, setLoading])

  useEffect(() => {
    void load()
  }, [load])

  const selectHistory = useCallback(
    async (item: HistoryItem) => {
      setSelectedId(item.id)
      const detail = await getHistoryDetail(item.id).catch(() => item)
      if (detail.taskType === 'text') {
        translateStore.hydrateFromHistory(detail)
        return
      }
      fileStore.hydrateFromHistory(detail)
      if (detail.taskId && isActiveFileStatus(detail.status)) {
        fileStore.startPolling(detail.taskId, detail.id)
      }
    },
    [fileStore, setSelectedId, translateStore],
  )

  const removeHistory = useCallback(
    async (item: HistoryItem) => {
      await deleteHistoryItem(item.id)
      removeItem(item.id)
      if (selectedId === item.id) {
        translateStore.reset()
        fileStore.clearTask()
      }
    },
    [fileStore, removeItem, selectedId, translateStore],
  )

  return {
    items,
    loading,
    selectedId,
    filter,
    keyword,
    page,
    pageSize,
    total,
    setFilter,
    setKeyword,
    setPage,
    resetSelection,
    load,
    selectHistory,
    removeHistory,
  }
}

import { create } from 'zustand'

import type { HistoryFilter, HistoryItem } from '@/types'

type HistoryState = {
  items: HistoryItem[]
  loading: boolean
  selectedId: string | null
  filter: HistoryFilter
  keyword: string
  page: number
  pageSize: number
  total: number
  setLoading: (loading: boolean) => void
  setList: (items: HistoryItem[], total: number, page?: number) => void
  setFilter: (filter: HistoryFilter) => void
  setKeyword: (keyword: string) => void
  setPage: (page: number) => void
  setSelectedId: (id: string | null) => void
  resetSelection: () => void
  upsertItem: (item: HistoryItem) => void
  updateItem: (id: string, patch: Partial<HistoryItem>) => void
  updateByTaskId: (taskId: string, patch: Partial<HistoryItem>) => void
  removeItem: (id: string) => void
  clear: () => void
}

function moveToFront(items: HistoryItem[], nextItem: HistoryItem) {
  return [nextItem, ...items.filter((item) => item.id !== nextItem.id)]
}

export const useHistoryStore = create<HistoryState>((set) => ({
  items: [],
  loading: false,
  selectedId: null,
  filter: 'all',
  keyword: '',
  page: 1,
  pageSize: 1000,
  total: 0,
  setLoading(loading) {
    set({ loading })
  },
  setList(items, total, page) {
    set((state) => ({
      items,
      total,
      page: page ?? state.page,
    }))
  },
  setFilter(filter) {
    set({ filter, page: 1 })
  },
  setKeyword(keyword) {
    set({ keyword, page: 1 })
  },
  setPage(page) {
    set({ page })
  },
  setSelectedId(selectedId) {
    set({ selectedId })
  },
  resetSelection() {
    set({ selectedId: null })
  },
  upsertItem(item) {
    set((state) => ({
      items: moveToFront(state.items, item),
      total: Math.max(state.total, state.items.some((entry) => entry.id === item.id) ? state.total : state.total + 1),
    }))
  },
  updateItem(id, patch) {
    set((state) => {
      const current = state.items.find((item) => item.id === id)
      if (!current) return state
      const nextItem = { ...current, ...patch }
      return { items: moveToFront(state.items, nextItem) }
    })
  },
  updateByTaskId(taskId, patch) {
    set((state) => {
      const current = state.items.find((item) => item.taskId === taskId)
      if (!current) return state
      const nextItem = { ...current, ...patch }
      return { items: moveToFront(state.items, nextItem) }
    })
  },
  removeItem(id) {
    set((state) => ({
      items: state.items.filter((item) => item.id !== id),
      total: Math.max(0, state.total - 1),
      selectedId: state.selectedId === id ? null : state.selectedId,
    }))
  },
  clear() {
    set({ items: [], selectedId: null, total: 0, page: 1 })
  },
}))

import { useMemo, useState } from 'react'
import { Typography } from 'antd'
import { Bot } from 'lucide-react'
import { toast } from 'sonner'

import { WorkspaceErrorBoundary } from '@/components/error-boundary/index'
import HistorySidebar from '@/components/history-sidebar/index'
import FilePanel from '@/components/file-panel/index'
import TextPanel from '@/components/text-panel/index'
import { useHistory } from '@/hooks/use-history'
import { useFileTranslateStore } from '@/store/file-translate'
import { useTranslateStore } from '@/store/translate'
import type { HistoryItem } from '@/types'

export default function WorkspacePage() {
  const [mode, setMode] = useState<'text' | 'file'>('text')
  const history = useHistory()
  const translateStore = useTranslateStore()
  const fileStore = useFileTranslateStore()

  const selectedItem = useMemo(
    () => history.items.find((item) => item.id === history.selectedId) ?? null,
    [history.items, history.selectedId],
  )

  const handleSelectHistory = async (item: HistoryItem) => {
    setMode(item.taskType)
    try {
      await history.selectHistory(item)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '历史记录加载失败')
    }
  }

  const handleDeleteHistory = async (item: HistoryItem) => {
    try {
      await history.removeHistory(item)
      toast.success('已删除历史记录')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '删除失败，请重试')
    }
  }

  const handleNewTranslation = () => {
    history.resetSelection()
    translateStore.reset()
    fileStore.clearTask()
    setMode('text')
  }

  const hasActiveHistory = Boolean(selectedItem)

  return (
    <div className="app-shell">
      <HistorySidebar
        items={history.items}
        loading={history.loading}
        filter={history.filter}
        keyword={history.keyword}
        selectedId={history.selectedId}
        onFilterChange={history.setFilter}
        onKeywordChange={history.setKeyword}
        onSelect={handleSelectHistory}
        onDelete={handleDeleteHistory}
        onNewTranslation={handleNewTranslation}
      />

      <main className="workspace-shell">
        <WorkspaceErrorBoundary>
          <section className="workspace-stage">
            {hasActiveHistory ? (
              <div className="workspace-active-header">
                <div className="workspace-active-title">
                  <div className="workspace-active-icon">
                    <Bot size={16} />
                  </div>
                  <div>
                    <Typography.Title level={4}>{selectedItem?.title}</Typography.Title>
                    <Typography.Text type="secondary">
                      {selectedItem?.taskType === 'text' ? '文本翻译模式' : '文件翻译模式'}
                    </Typography.Text>
                  </div>
                </div>
                <div className="workspace-active-badge">
                  {selectedItem?.taskType === 'text' ? 'Text' : 'File'}
                </div>
              </div>
            ) : (
              <>
                <div className="workspace-hero">
                  <div className="workspace-hero-icon">
                    <Bot size={34} />
                  </div>
                  <Typography.Title level={3} className="workspace-hero-title">智能医药翻译系统</Typography.Title>
                  <Typography.Paragraph className="workspace-hero-desc">
                    支持文本、PDF、Word 文档翻译，完美保留原始排版。
                  </Typography.Paragraph>
                </div>

                <div className="workspace-mode-switch">
                  <button
                    type="button"
                    className={`workspace-mode-button ${mode === 'text' ? 'is-active' : ''}`}
                    onClick={() => setMode('text')}
                  >
                    文本翻译
                  </button>
                  <button
                    type="button"
                    className={`workspace-mode-button ${mode === 'file' ? 'is-active' : ''}`}
                    onClick={() => setMode('file')}
                  >
                    文件翻译
                  </button>
                </div>
              </>
            )}

            <div className="workspace-panel-shell">
              {(selectedItem?.taskType ?? mode) === 'text' ? <TextPanel /> : <FilePanel />}
            </div>
          </section>
        </WorkspaceErrorBoundary>
      </main>
    </div>
  )
}

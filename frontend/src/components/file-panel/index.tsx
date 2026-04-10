import { Alert, Card, Empty, Typography } from 'antd'
import { Suspense, lazy, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import DownloadBar from '@/components/download-bar/index'
import FileList from '@/components/file-panel/file-list'
import FileProgress from '@/components/file-panel/file-progress'
import FileUpload from '@/components/file-panel/file-upload'
import LangSelector from '@/components/lang-selector/index'
import { useFileTranslation } from '@/hooks/use-file-translation'
import type { LanguageCode, SupportedLanguageCode } from '@/types'
import { formatLanguage, isActiveFileStatus } from '@/utils/format'

const PdfViewer = lazy(() => import('@/components/file-panel/pdf-viewer'))

export default function FilePanel() {
  const { currentTask, start, retry, cancel, reset } = useFileTranslation()
  const [sourceLang, setSourceLang] = useState<LanguageCode>('auto')
  const [targetLang, setTargetLang] = useState<SupportedLanguageCode>('en')

  useEffect(() => {
    if (!currentTask) return
    setSourceLang(currentTask.sourceLang)
    setTargetLang(currentTask.targetLang)
  }, [currentTask])

  const activeTask = currentTask
  const isBusy = isActiveFileStatus(activeTask?.status)
  const isPreviewReady = activeTask?.status === 'done'
  const showPreviewOnly = activeTask?.status === 'done'
  const showComposeLayout = !activeTask
  const previewTaskKey = activeTask?.taskId ?? activeTask?.historyId
  const nextHistoryId = useMemo(() => {
    if (!activeTask?.historyId) return undefined
    if (['failed', 'cancelled'].includes(activeTask.status)) return activeTask.historyId
    if (activeTask.status === 'done' && activeTask.sourceLang === sourceLang && activeTask.targetLang === targetLang) {
      return activeTask.historyId
    }
    return undefined
  }, [activeTask, sourceLang, targetLang])

  const handleSelectFile = async (file: File) => {
    if (activeTask && isBusy) {
      toast.error('当前已有文件在处理中，请等待完成后再上传新文件')
      return
    }

    const reuseHistoryId = nextHistoryId
    if (activeTask && !isBusy) reset()

    try {
      await start({
        file,
        sourceLang,
        targetLang,
        historyId: reuseHistoryId,
      })
      toast.success('文件已上传，系统已自动开始翻译')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '文件翻译提交失败')
    }
  }

  const handleRetry = async () => {
    try {
      await retry()
      toast.success('已重新发起翻译')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '重试失败')
    }
  }

  const handleCancel = async () => {
    try {
      await cancel()
      toast.success('已取消翻译任务')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '取消失败')
    }
  }

  return (
    <div className={`panel-block mode-panel-card ${showComposeLayout ? 'is-compose' : ''}`}>
      {showPreviewOnly ? (
        <section >
          {/* <div className="preview-heading">
            <div>
              <Typography.Title level={5}>双语对照预览</Typography.Title>
              <Typography.Text type="secondary">
                翻译成功后展示翻译前与翻译后的 PDF 对照预览；下载仅提供纯译文 PDF。
              </Typography.Text>
            </div>
            <DownloadBar
              taskId={previewTaskKey}
              title={activeTask.name}
              targetLang={formatLanguage(activeTask.targetLang)}
            />
          </div> */}
          <DownloadBar
              taskId={previewTaskKey}
              title={activeTask.name}
              targetLang={formatLanguage(activeTask.targetLang)}
            />

          <Suspense fallback={<div className="viewer-loading">预览加载中...</div>}>
            <div className="pdf-compare-grid">
              <PdfViewer
                title="翻译前 PDF"
                ready={isPreviewReady}
                endpoint={previewTaskKey ? `/api/translate/source/${previewTaskKey}` : undefined}
                emptyDescription="翻译完成后这里展示原文件 PDF 预览"
              />
              <PdfViewer
                title="翻译后 PDF"
                ready={isPreviewReady}
                endpoint={previewTaskKey ? `/api/translate/result/${previewTaskKey}` : undefined}
                emptyDescription="翻译完成后这里展示纯译文 PDF 预览"
              />
            </div>
          </Suspense>
        </section>
      ) : (
        <section className={`translate-pane translate-pane-full mode-panel-center ${showComposeLayout ? 'is-compose' : ''}`}>
          <LangSelector
            sourceLang={sourceLang}
            targetLang={targetLang}
            onSourceLangChange={setSourceLang}
            onTargetLangChange={setTargetLang}
            disabled={isBusy}
          />

          <div className="mode-compose-shell">
            <FileUpload disabled={isBusy} onFileSelected={handleSelectFile} />
            <FileList
              fileName={activeTask?.name}
              fileSize={activeTask?.size}
              removable={!isBusy && !activeTask?.taskId}
              onRemove={() => reset()}
            />
            {activeTask ? (
              <FileProgress
                status={activeTask.status}
                progress={activeTask.uploadProgress}
                error={activeTask.error}
                onRetry={handleRetry}
                onCancel={handleCancel}
              />
            ) : null}
          </div>

          {/* <Typography.Text type="secondary" className="surface-note align-center">
            文件翻译进行中时，你仍可切换查看其他历史记录，也可继续使用文本翻译。
          </Typography.Text> */}

          {/* {activeTask?.status === 'queued' ? <Alert type="info" showIcon message="当前任务排队中，不展示排队序号。" /> : null} */}
          {/* {!activeTask ? <Empty description="上传文件后自动开始翻译，完成后这里展示翻译前后文档对比图。" /> : null} */}
        </section>
      )}
    </div>
  )
}

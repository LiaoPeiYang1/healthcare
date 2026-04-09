import { Card, Empty, Spin, Typography } from 'antd'
import { useEffect, useState } from 'react'

import { request } from '@/api/client'

type PdfViewerProps = {
  endpoint?: string
  ready?: boolean
  title: string
  emptyDescription: string
}

export default function PdfViewer({ endpoint, ready = false, title, emptyDescription }: PdfViewerProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [blobUrl, setBlobUrl] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    let localBlobUrl: string | null = null

    async function loadPdfBlob() {
      if (!endpoint || !ready) {
        setLoading(false)
        setError(null)
        setBlobUrl((current) => {
          if (current) URL.revokeObjectURL(current)
          return null
        })
        return
      }

      setLoading(true)
      setError(null)

      try {
        const blob = await request<Blob>(endpoint, { parseAs: 'blob' })
        localBlobUrl = URL.createObjectURL(blob)
        if (cancelled) return
        setBlobUrl((current) => {
          if (current) URL.revokeObjectURL(current)
          return localBlobUrl
        })
      } catch (renderError) {
        if (!cancelled) {
          setBlobUrl((current) => {
            if (current) URL.revokeObjectURL(current)
            return null
          })
          setError(renderError instanceof Error ? renderError.message : 'PDF 预览失败')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void loadPdfBlob()
    return () => {
      cancelled = true
      if (localBlobUrl) URL.revokeObjectURL(localBlobUrl)
    }
  }, [endpoint, ready])

  return (
    <Card bordered={false} className="pdf-preview-card">
      <Typography.Title level={5}>{title}</Typography.Title>
      {!ready || !endpoint ? (
        <Empty description={emptyDescription} />
      ) : loading ? (
        <div className="viewer-loading">
          <Spin size="large" />
        </div>
      ) : error ? (
        <Empty description={error} />
      ) : (
        <iframe
          src={blobUrl ?? undefined}
          title={title}
          className="pdf-frame"
        />
      )}
    </Card>
  )
}

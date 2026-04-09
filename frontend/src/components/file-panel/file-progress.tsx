import { Alert, Button, Progress, Typography } from 'antd'

import type { FileTaskStatus } from '@/types'
import { statusLabel } from '@/utils/format'

type FileProgressProps = {
  status?: FileTaskStatus
  progress?: number
  error?: string
  onRetry?: () => void
  onCancel?: () => void
}

export default function FileProgress({ status, progress = 0, error, onRetry, onCancel }: FileProgressProps) {
  if (!status) return null

  return (
    <div className="panel-stack compact-gap">
      <div className="file-status-row">
        <Typography.Text strong>当前状态</Typography.Text>
        <Typography.Text>{statusLabel(status)}</Typography.Text>
      </div>
      <Progress percent={status === 'done' ? 100 : progress} status={status === 'failed' ? 'exception' : undefined} />
      {error ? <Alert type="error" showIcon message={error} /> : null}
      <div className="action-row compact-actions">
        {status === 'failed' && onRetry ? <Button onClick={onRetry}>重试</Button> : null}
        {['queued', 'translating'].includes(status) && onCancel ? <Button onClick={onCancel}>取消翻译</Button> : null}
      </div>
    </div>
  )
}

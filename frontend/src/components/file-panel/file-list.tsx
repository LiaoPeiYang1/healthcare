import { Button, Card, Typography } from 'antd'
import { X } from 'lucide-react'

import { formatFileSize } from '@/utils/format'

type FileListProps = {
  fileName?: string
  fileSize?: number
  removable?: boolean
  onRemove?: () => void
}

export default function FileList({ fileName, fileSize, removable = false, onRemove }: FileListProps) {
  if (!fileName) return null

  return (
    <Card bordered={false} className="file-summary-card">
      <div className="file-summary-head">
        <div>
          <Typography.Text strong>{fileName}</Typography.Text>
          <div className="history-item-meta">{fileSize ? formatFileSize(fileSize) : '已上传文件'}</div>
        </div>
        {removable && onRemove ? <Button type="text" icon={<X size={16} />} onClick={onRemove} /> : null}
      </div>
    </Card>
  )
}

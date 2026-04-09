import { Button, Typography } from 'antd'
import { FileText, MessageSquare, Trash2 } from 'lucide-react'

import type { HistoryItem } from '@/types'
import { cn } from '@/utils/cn'
import { formatHistoryDate } from '@/utils/format'
type HistoryItemCardProps = {
  item: HistoryItem
  active: boolean
  onSelect: () => void
  onDelete: () => void
}

export default function HistoryItemCard({ item, active, onSelect, onDelete }: HistoryItemCardProps) {
  return (
    <button type="button" className={cn('history-item-card', active && 'is-active')} onClick={onSelect}>
      <div className="history-item-top">
        <div className="history-item-main">
          <div className="history-item-icon">
            {item.taskType === 'text' ? <MessageSquare size={14} /> : <FileText size={14} />}
          </div>
          <div className="history-item-copy">
            <Typography.Text strong>{item.title}</Typography.Text>
            {/* <div className="history-item-date">{formatHistoryDate(item.updatedAt)}</div> */}
          </div>
        </div>
        <div className="history-item-actions" onClick={(event) => event.stopPropagation()}>
          <Button type="text" danger icon={<Trash2 size={14} />} onClick={onDelete} />
        </div>
      </div>
    </button>
  )
}

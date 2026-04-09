import { Input, Segmented } from 'antd'

import type { HistoryFilter } from '@/types'

type HistorySearchProps = {
  keyword: string
  filter: HistoryFilter
  onKeywordChange: (value: string) => void
  onFilterChange: (value: HistoryFilter) => void
}

export default function HistorySearch({ keyword, filter, onKeywordChange, onFilterChange }: HistorySearchProps) {
  return (
    <div className="sidebar-search">
      <Input
        size="large"
        placeholder="搜索标题 / 文件名"
        value={keyword}
        onChange={(event) => onKeywordChange(event.target.value)}
      />
      <Segmented
        block
        value={filter}
        options={[
          { label: '全部', value: 'all' },
          { label: '文本', value: 'text' },
          { label: '文件', value: 'file' },
        ]}
        onChange={(value) => onFilterChange(value as HistoryFilter)}
      />
    </div>
  )
}

import { Button, Dropdown, Empty, Modal, Spin, Typography } from 'antd'
import type { MenuProps } from 'antd'
import { ChevronUp, LogOut } from 'lucide-react'

import HistorySearch from '@/components/history-sidebar/history-search'
import HistoryItemCard from '@/components/history-sidebar/history-item'
import { useAuthStore } from '@/store/auth'
import type { HistoryFilter, HistoryItem } from '@/types'

type HistorySidebarProps = {
  items: HistoryItem[]
  loading: boolean
  filter: HistoryFilter
  keyword: string
  selectedId: string | null
  onFilterChange: (value: HistoryFilter) => void
  onKeywordChange: (value: string) => void
  onSelect: (item: HistoryItem) => void
  onDelete: (item: HistoryItem) => void
  onNewTranslation: () => void
}

export default function HistorySidebar(props: HistorySidebarProps) {
  const {
    items,
    loading,
    filter,
    keyword,
    selectedId,
    onFilterChange,
    onKeywordChange,
    onSelect,
    onDelete,
    onNewTranslation,
  } = props
  const userInfo = useAuthStore((state) => state.userInfo)
  const logout = useAuthStore((state) => state.logout)

  const confirmDelete = (item: HistoryItem) => {
    Modal.confirm({
      title: '确认删除',
      content: '删除后不可恢复，将同时删除云端源文件与翻译结果。确认删除？',
      okText: '确认删除',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: () => onDelete(item),
    })
  }

  const groupedItems = [
    { key: 'text', label: '文本翻译', items: items.filter((item) => item.taskType === 'text') },
    { key: 'file', label: '文件翻译', items: items.filter((item) => item.taskType === 'file') },
  ].filter((group) => group.items.length > 0)

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'logout',
      label: '退出登录',
      icon: <LogOut size={14} />,
    },
  ]

  return (
    <aside className="history-sidebar">
      <Button type="default" size="large" block onClick={onNewTranslation} className="history-new-chat">
        + 开启新对话
      </Button>

      <HistorySearch
        keyword={keyword}
        filter={filter}
        onKeywordChange={onKeywordChange}
        onFilterChange={onFilterChange}
      />

      <div className="history-list-wrap">
        {loading ? (
          <div className="history-empty"><Spin /></div>
        ) : items.length ? (
          <div className="history-list">
            {groupedItems.map((group) => (
              <section key={group.key} className="history-group">
                <div className="history-group-title">
                  <span>{group.label}</span>
                  <span>{group.items.length}</span>
                </div>
                <div className="history-group-list">
                  {group.items.map((item) => (
                    <HistoryItemCard
                      key={item.id}
                      item={item}
                      active={selectedId === item.id}
                      onSelect={() => onSelect(item)}
                      onDelete={() => confirmDelete(item)}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>
        ) : (
          <div className="history-empty"><Empty description="暂无历史记录" /></div>
        )}
      </div>

      {userInfo ? (
        <Dropdown
          trigger={['click']}
          placement="topLeft"
          menu={{
            items: userMenuItems,
            onClick: ({ key }) => {
              if (key === 'logout') {
                void logout()
              }
            },
          }}
        >
          <button type="button" className="history-sidebar-user-trigger">
            <div className="history-sidebar-user-main">
              <div className="history-sidebar-user-avatar">
                {userInfo.name.slice(0, 1).toUpperCase()}
              </div>
              <Typography.Text className="history-sidebar-user-name">{userInfo.name}</Typography.Text>
            </div>
            <ChevronUp size={16} className="history-sidebar-user-chevron" />
          </button>
        </Dropdown>
      ) : (
        <div className="history-sidebar-footer">
          <span className="status-dot" />
          <Typography.Text>AI 翻译系统已就绪</Typography.Text>
        </div>
      )}
    </aside>
  )
}

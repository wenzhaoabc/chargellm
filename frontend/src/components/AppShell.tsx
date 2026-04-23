import { useEffect, useMemo, useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { App, Button, Dropdown, Empty, Input, Modal, Space, Typography } from 'antd'
import {
  DeleteOutlined,
  EditOutlined,
  MessageOutlined,
  MoreOutlined,
  PlusOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import {
  CONVERSATION_HISTORY_CHANGED_EVENT,
  NEW_CONVERSATION_EVENT,
  OPEN_CONVERSATION_EVENT,
  deleteConversation,
  getActiveConversationId,
  listConversationHistory,
  renameConversation,
  setActiveConversationId,
  type ConversationRecord,
} from '@/api/conversations'

export function AppShell() {
  const navigate = useNavigate()
  const { modal, message } = App.useApp()
  const [history, setHistory] = useState<ConversationRecord[]>(() => listConversationHistory())
  const [activeId, setActiveIdState] = useState(() => getActiveConversationId())
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    const refresh = () => {
      setHistory(listConversationHistory())
      setActiveIdState(getActiveConversationId())
    }
    window.addEventListener(CONVERSATION_HISTORY_CHANGED_EVENT, refresh)
    window.addEventListener('storage', refresh)
    return () => {
      window.removeEventListener(CONVERSATION_HISTORY_CHANGED_EVENT, refresh)
      window.removeEventListener('storage', refresh)
    }
  }, [])

  const handleNewConversation = () => {
    setActiveConversationId('')
    setActiveIdState('')
    navigate('/chat')
    window.dispatchEvent(new Event(NEW_CONVERSATION_EVENT))
  }

  const handleOpen = (conversationId: string) => {
    setActiveConversationId(conversationId)
    setActiveIdState(conversationId)
    navigate('/chat')
    window.dispatchEvent(new CustomEvent(OPEN_CONVERSATION_EVENT, { detail: { conversationId } }))
  }

  const handleDelete = (record: ConversationRecord) => {
    modal.confirm({
      title: '删除对话',
      content: `确定删除「${record.title || '未命名对话'}」吗？此操作不可撤销。`,
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: () => {
        deleteConversation(record.id)
        message.success('已删除')
      },
    })
  }

  const handleRename = (record: ConversationRecord) => {
    let nextTitle = record.title
    modal.confirm({
      title: '重命名对话',
      content: (
        <Input
          defaultValue={record.title}
          onChange={(e) => {
            nextTitle = e.target.value
          }}
          maxLength={64}
        />
      ),
      okText: '保存',
      cancelText: '取消',
      onOk: () => {
        const trimmed = (nextTitle || '').trim()
        if (!trimmed) {
          message.warning('标题不能为空')
          return Promise.reject()
        }
        renameConversation(record.id, trimmed)
        message.success('已重命名')
      },
    })
  }

  const filteredSearchResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    if (!q) return history
    return history.filter((r) =>
      r.title.toLowerCase().includes(q) ||
      r.turns.some((t) => t.question.toLowerCase().includes(q) || t.answer.toLowerCase().includes(q)),
    )
  }, [history, searchQuery])

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">CL</div>
          <div>
            <div className="brand-title">电池健康诊断 AI</div>
            <div className="brand-subtitle">Battery Health Assistant</div>
          </div>
        </div>

        <button className="new-chat-button" type="button" onClick={handleNewConversation}>
          <PlusOutlined />
          <span>新建对话</span>
        </button>

        <button className="sidebar-tool-button" type="button" onClick={() => setSearchOpen(true)}>
          <SearchOutlined />
          <span>搜索对话</span>
        </button>

        <div className="conversation-rail">
          <div className="rail-title">当前与历史</div>
          {!activeId && (
            <button className="conversation-chip active" type="button" onClick={handleNewConversation}>
              当前对话
              <small>尚未保存诊断结果</small>
            </button>
          )}
          {history.length === 0 && <div className="empty-conversation-list">暂无历史对话</div>}
          {history.map((conversation) => (
            <ConversationItem
              key={conversation.id}
              record={conversation}
              active={conversation.id === activeId}
              onOpen={() => handleOpen(conversation.id)}
              onDelete={() => handleDelete(conversation)}
              onRename={() => handleRename(conversation)}
            />
          ))}
        </div>

        <div className="sidebar-note">
          <div className="sidebar-note-title">访问状态</div>
          <p>普通用户只进入诊断对话；后台管理能力保留在独立管理员路由。</p>
        </div>
      </aside>

      <div className="main-area">
        <main className="content">
          <Outlet />
        </main>
      </div>

      <Modal
        open={searchOpen}
        title="搜索对话"
        footer={null}
        onCancel={() => { setSearchOpen(false); setSearchQuery('') }}
        width={520}
      >
        <Input.Search
          autoFocus
          placeholder="按标题或消息内容搜索"
          allowClear
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{ marginBottom: 12 }}
        />
        {filteredSearchResults.length === 0 ? (
          <Empty description="没有匹配的对话" />
        ) : (
          <Space direction="vertical" size={6} style={{ width: '100%', maxHeight: 360, overflowY: 'auto' }}>
            {filteredSearchResults.map((r) => (
              <div
                key={r.id}
                style={{
                  padding: 10,
                  border: '1px solid #f0f0f0',
                  borderRadius: 6,
                  cursor: 'pointer',
                }}
                onClick={() => {
                  setSearchOpen(false)
                  setSearchQuery('')
                  handleOpen(r.id)
                }}
              >
                <Space size={6}>
                  <MessageOutlined />
                  <Typography.Text strong>{r.title || '未命名对话'}</Typography.Text>
                </Space>
                <div>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {r.updatedAt || r.createdAt} · {r.turns.length} 轮
                  </Typography.Text>
                </div>
              </div>
            ))}
          </Space>
        )}
      </Modal>
    </div>
  )
}

function ConversationItem({
  record,
  active,
  onOpen,
  onDelete,
  onRename,
}: {
  record: ConversationRecord
  active: boolean
  onOpen: () => void
  onDelete: () => void
  onRename: () => void
}) {
  return (
    <div className={`conversation-chip${active ? ' active' : ''}`} role="button">
      <button type="button" className="conversation-chip-main" onClick={onOpen}>
        <span className="conversation-chip-title">{record.title || '未命名对话'}</span>
        <small>{record.updatedAt || record.createdAt}</small>
      </button>
      <Dropdown
        menu={{
          items: [
            { key: 'rename', icon: <EditOutlined />, label: '重命名', onClick: onRename },
            { type: 'divider' },
            { key: 'delete', icon: <DeleteOutlined />, label: '删除', danger: true, onClick: onDelete },
          ],
        }}
        trigger={['click']}
        placement="bottomRight"
      >
        <Button
          type="text"
          size="small"
          className="conversation-chip-menu"
          icon={<MoreOutlined />}
          onClick={(e) => e.stopPropagation()}
        />
      </Dropdown>
    </div>
  )
}

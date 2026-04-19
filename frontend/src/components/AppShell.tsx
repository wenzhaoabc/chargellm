import { useEffect, useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import {
  CONVERSATION_HISTORY_CHANGED_EVENT,
  NEW_CONVERSATION_EVENT,
  OPEN_CONVERSATION_EVENT,
  getActiveConversationId,
  listConversationHistory,
  setActiveConversationId,
  type ConversationRecord,
} from '@/api/conversations'

export function AppShell() {
  const navigate = useNavigate()
  const [history, setHistory] = useState<ConversationRecord[]>(() => listConversationHistory())
  const [activeConversationId, setActiveConversationIdState] = useState(() => getActiveConversationId())

  useEffect(() => {
    const refresh = () => {
      setHistory(listConversationHistory())
      setActiveConversationIdState(getActiveConversationId())
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
    setActiveConversationIdState('')
    navigate('/chat')
    window.dispatchEvent(new Event(NEW_CONVERSATION_EVENT))
  }

  const handleOpenConversation = (conversationId: string) => {
    setActiveConversationId(conversationId)
    setActiveConversationIdState(conversationId)
    navigate('/chat')
    window.dispatchEvent(new CustomEvent(OPEN_CONVERSATION_EVENT, { detail: { conversationId } }))
  }

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
          <span>+</span>
          新建对话
        </button>

        <button className="sidebar-tool-button" type="button" aria-label="搜索对话">
          <span>⌕</span>
          搜索对话
        </button>

        <div className="conversation-rail">
          <div className="rail-title">当前与历史</div>
          {!activeConversationId ? (
            <button className="conversation-chip active" type="button" onClick={handleNewConversation}>
              当前对话
              <small>尚未保存诊断结果</small>
            </button>
          ) : null}
          {history.length === 0 ? <div className="empty-conversation-list">暂无历史对话</div> : null}
          {history.map((conversation) => (
            <button
              key={conversation.id}
              className={`conversation-chip${conversation.id === activeConversationId ? ' active' : ''}`}
              type="button"
              onClick={() => handleOpenConversation(conversation.id)}
            >
              {conversation.title}
              <small>{conversation.updatedAt || conversation.createdAt}</small>
            </button>
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
    </div>
  )
}

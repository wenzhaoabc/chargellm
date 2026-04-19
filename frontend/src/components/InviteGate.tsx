import type { FormEvent } from 'react'
import { useEffect, useState } from 'react'
import { getInviteCode, setInviteCode, startInviteSession } from '@/api/auth'

type Props = {
  onConfirmed?: (code: string) => void
}

const inviteErrorMessages: Record<string, string> = {
  invite_not_found: '邀请码不存在或已停用，请核对后重新输入。',
  invite_disabled: '邀请码不存在或已停用，请核对后重新输入。',
  invite_exhausted: '邀请码调用次数已用尽，请联系管理员重新分配。',
  invite_expired: '邀请码已过期，请联系管理员重新分配。',
}

function normalizeInviteError(error: unknown) {
  const fallback = '邀请码验证失败，请稍后重试。'
  if (!(error instanceof Error)) {
    return fallback
  }
  try {
    const payload = JSON.parse(error.message) as { detail?: unknown }
    if (typeof payload.detail === 'string') {
      return inviteErrorMessages[payload.detail] || fallback
    }
  } catch {
    return inviteErrorMessages[error.message] || error.message || fallback
  }
  return fallback
}

export function InviteGate({ onConfirmed }: Props) {
  const [code, setCodeValue] = useState('')
  const [savedCode, setSavedCode] = useState(getInviteCode())
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)

  useEffect(() => {
    setSavedCode(getInviteCode())
  }, [])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const normalized = code.trim()
    if (!normalized) {
      return
    }
    setPending(true)
    setError('')
    try {
      await startInviteSession(normalized)
      setInviteCode(normalized)
      setSavedCode(normalized)
      onConfirmed?.(normalized)
    } catch (error) {
      setError(normalizeInviteError(error))
    } finally {
      setPending(false)
    }
  }

  return (
    <section className="panel invite-panel">
      <div className="panel-header">
        <div>
          <div className="section-kicker">邀请码入口</div>
          <h2>先输入邀请码，再进入示例体验</h2>
        </div>
        <span className={`status-pill ${savedCode ? 'success' : 'warning'}`}>
          {savedCode ? '已解锁' : '未解锁'}
        </span>
      </div>

      <p className="muted">
        这个 demo 不要求手机号。输入邀请码后即可浏览示例电池、发起聊天诊断和查看 SSE 流式结果。
      </p>

      <form className="invite-form" onSubmit={handleSubmit}>
        <input
          className="input"
          value={code}
          onChange={(event) => setCodeValue(event.target.value)}
          placeholder="请输入管理员分配的邀请码"
          disabled={pending}
        />
        <button className="button primary" type="submit" disabled={pending}>
          {pending ? '验证中' : '解锁体验'}
        </button>
      </form>

      {error ? <div className="inline-info danger">{error}</div> : null}

      {savedCode ? (
        <div className="inline-info">
          当前邀请码：<strong>{savedCode}</strong>
        </div>
      ) : (
        <div className="inline-info subtle">未输入邀请码时，部分交互会保持只读。</div>
      )}
    </section>
  )
}

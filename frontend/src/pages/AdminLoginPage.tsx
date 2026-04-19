import type { FormEvent } from 'react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getAdminToken, loginAdmin } from '@/api/admin'

export function AdminLoginPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('ChangeMe123!')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)

  useEffect(() => {
    if (getAdminToken()) {
      navigate('/admin', { replace: true })
    }
  }, [navigate])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setPending(true)
      setError('')
    try {
      await loginAdmin(username, password)
      navigate('/admin', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : '管理员登录失败')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="page-stack compact-page">
      <section className="panel login-panel">
        <div className="panel-header">
          <div>
            <div className="section-kicker">管理员登录</div>
            <h2>输入管理员账号和密码</h2>
          </div>
          <span className="status-pill warning">Admin</span>
        </div>

        <form className="question-form" onSubmit={handleSubmit}>
          <input
            className="input"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="管理员账号"
          />
          <input
            className="input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="管理员密码"
          />
          {error ? <div className="inline-info danger">{error}</div> : null}
          <button className="button primary" type="submit" disabled={pending}>
            {pending ? '登录中...' : '登录后台'}
          </button>
        </form>
      </section>
    </div>
  )
}

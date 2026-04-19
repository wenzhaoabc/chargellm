import type { FormEvent } from 'react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  createAdminInvite,
  createAdminDataset,
  deleteAdminInvite,
  deleteAdminDataset,
  getAdminToken,
  importAdminDatasetFromMysql,
  listAdminDatasets,
  listAdminInvites,
  listAdminRuns,
  listAdminUsers,
  updateAdminDataset,
  updateAdminInvite,
} from '@/api/admin'
import type { AdminInviteRow, AdminRunRow, AdminUserRow, BatteryExample } from '@/api/types'

type InviteDraft = {
  name: string
  usageLimit: number
  perUserQuota: number
  status: AdminInviteRow['status']
}

function toInviteDraft(invite: AdminInviteRow): InviteDraft {
  return {
    name: invite.name,
    usageLimit: invite.usageLimit,
    perUserQuota: invite.perUserQuota,
    status: invite.status,
  }
}

function numberOrOne(value: number) {
  return Number.isFinite(value) && value > 0 ? value : 1
}

export function AdminPage() {
  const [invites, setInvites] = useState<AdminInviteRow[]>([])
  const [users, setUsers] = useState<AdminUserRow[]>([])
  const [runs, setRuns] = useState<AdminRunRow[]>([])
  const [datasets, setDatasets] = useState<BatteryExample[]>([])
  const [drafts, setDrafts] = useState<Record<number, InviteDraft>>({})
  const [name, setName] = useState('公测体验码')
  const [code, setCode] = useState('')
  const [maxUses, setMaxUses] = useState(20)
  const [perUserQuota, setPerUserQuota] = useState(10)
  const [datasetTitle, setDatasetTitle] = useState('专业演示数据')
  const [datasetProblemType, setDatasetProblemType] = useState('待诊断')
  const [datasetCapacityRange, setDatasetCapacityRange] = useState('待评估')
  const [datasetDescription, setDatasetDescription] = useState('专业演示数据')
  const [datasetContent, setDatasetContent] = useState('')
  const [mysqlPhone, setMysqlPhone] = useState('')
  const [mysqlStartTime, setMysqlStartTime] = useState('')
  const [mysqlEndTime, setMysqlEndTime] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const adminToken = getAdminToken()

  const refreshAdminData = async () => {
    if (!adminToken) {
      setInvites([])
      setUsers([])
      setRuns([])
      setDatasets([])
      setDrafts({})
      return
    }
    setLoading(true)
    setMessage('')
    try {
      const inviteRows = await listAdminInvites()
      const datasetRows = await listAdminDatasets()
      setInvites(inviteRows)
      setDatasets(datasetRows)
      setUsers(listAdminUsers())
      setRuns(listAdminRuns())
      setDrafts(Object.fromEntries(inviteRows.map((invite) => [invite.id, toInviteDraft(invite)])))
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '后台数据读取失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refreshAdminData()
  }, [adminToken])

  const overview = useMemo(() => {
    const usageLimit = invites.reduce((sum, invite) => sum + invite.usageLimit, 0)
    const usageCount = invites.reduce((sum, invite) => sum + invite.usageCount, 0)
    return {
      inviteCount: invites.length,
      activeCount: invites.filter((invite) => invite.status === 'active').length,
      usageLimit,
      usageCount,
      userCount: users.length,
      runCount: runs.length,
      datasetCount: datasets.length,
    }
  }, [datasets.length, invites, runs.length, users.length])

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setMessage('')
    try {
      const invite = await createAdminInvite({
        name,
        code: code.trim() || undefined,
        max_uses: maxUses,
        per_user_quota: perUserQuota,
      })
      setInvites((current) => [invite, ...current])
      setDrafts((current) => ({ ...current, [invite.id]: toInviteDraft(invite) }))
      setCode('')
      setMessage('邀请码已创建')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '邀请码创建失败')
    } finally {
      setLoading(false)
    }
  }

  const updateDraft = (inviteId: number, patch: Partial<InviteDraft>) => {
    setDrafts((current) => ({
      ...current,
      [inviteId]: {
        ...current[inviteId],
        ...patch,
      },
    }))
  }

  const handleUpdate = async (invite: AdminInviteRow) => {
    const draft = drafts[invite.id] || toInviteDraft(invite)
    setLoading(true)
    setMessage('')
    try {
      const updated = await updateAdminInvite(invite.id, {
        name: draft.name.trim() || invite.name,
        max_uses: numberOrOne(draft.usageLimit),
        per_user_quota: numberOrOne(draft.perUserQuota),
        is_active: draft.status === 'active',
      })
      setInvites((current) => current.map((item) => (item.id === updated.id ? updated : item)))
      setDrafts((current) => ({ ...current, [updated.id]: toInviteDraft(updated) }))
      setMessage('邀请码已更新')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '邀请码更新失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (invite: AdminInviteRow) => {
    setLoading(true)
    setMessage('')
    try {
      await deleteAdminInvite(invite.id)
      setInvites((current) => current.filter((item) => item.id !== invite.id))
      setDrafts((current) => {
        const next = { ...current }
        delete next[invite.id]
        return next
      })
      setMessage('邀请码已删除')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '邀请码删除失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateDataset = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setMessage('')
    try {
      const dataset = await createAdminDataset({
        title: datasetTitle.trim() || '专业演示数据',
        problem_type: datasetProblemType.trim() || '待诊断',
        capacity_range: datasetCapacityRange.trim() || '待评估',
        description: datasetDescription.trim() || '专业演示数据',
        sort_order: 0,
        is_active: true,
        file_name: 'dataset.json',
        content: datasetContent.trim() || undefined,
      })
      setDatasets((current) => [dataset, ...current])
      setMessage('演示数据已新增')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '演示数据新增失败')
    } finally {
      setLoading(false)
    }
  }

  const handleToggleDataset = async (dataset: BatteryExample) => {
    if (!dataset.datasetId) {
      return
    }
    setLoading(true)
    setMessage('')
    try {
      const updated = await updateAdminDataset(dataset.datasetId, { is_active: !dataset.isActive })
      setDatasets((current) => current.map((item) => (item.datasetId === updated.datasetId ? updated : item)))
      setMessage('演示数据已更新')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '演示数据更新失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteDataset = async (dataset: BatteryExample) => {
    if (!dataset.datasetId) {
      return
    }
    setLoading(true)
    setMessage('')
    try {
      await deleteAdminDataset(dataset.datasetId)
      setDatasets((current) => current.filter((item) => item.datasetId !== dataset.datasetId))
      setMessage('演示数据已删除')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '演示数据删除失败')
    } finally {
      setLoading(false)
    }
  }

  const handleMysqlImport = async () => {
    setLoading(true)
    setMessage('')
    try {
      const dataset = await importAdminDatasetFromMysql({
        phone: mysqlPhone,
        start_time: mysqlStartTime,
        end_time: mysqlEndTime,
        title: datasetTitle,
      })
      setDatasets((current) => [dataset, ...current])
      setMessage('平台数据已抽取')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '平台抽取接口待配置')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="admin-console">
      <aside className="admin-sidebar" aria-label="后台侧边栏">
        <Link className="admin-sidebar-brand" to="/admin">
          <span>CL</span>
          <div>
            <strong>ChargeLLM Admin</strong>
            <small>电池诊断大模型后台</small>
          </div>
        </Link>
        <nav className="admin-sidebar-nav" aria-label="后台模块导航">
          <a href="#admin-overview">工作台</a>
          <a href="#admin-datasets">演示数据</a>
          <a href="#admin-invites">邀请码</a>
          <a href="#admin-users">用户配额</a>
          <a href="#admin-conversations">历史对话</a>
        </nav>
        <div className="admin-sidebar-foot">
          <span>当前环境</span>
          <strong>{adminToken ? '已建立临时管理会话' : '等待管理员登录'}</strong>
          <Link to="/" className="admin-back-link">
            返回产品页
          </Link>
        </div>
      </aside>

      <section className="admin-workspace" aria-label="后台管理工作区">
        <header className="admin-topbar" role="banner" aria-label="后台顶部栏">
          <div>
            <div className="section-kicker">Management Console</div>
            <h1>后台管理系统</h1>
          </div>
          <div className="admin-topbar-actions">
            <span className={`status-pill ${adminToken ? 'success' : 'warning'}`}>{adminToken ? '管理员在线' : '需要登录'}</span>
            <Link className="button secondary" to="/admin/login">
              管理员登录
            </Link>
          </div>
        </header>

        <main className="admin-page">
          <section id="admin-overview" className="panel admin-panel">
        <div className="panel-header">
          <div>
            <div className="section-kicker">管理员后台</div>
            <h2>后台概览</h2>
          </div>
          <span className={`status-pill ${adminToken ? 'success' : 'warning'}`}>{adminToken ? '已登录' : '需要登录'}</span>
        </div>

        {!adminToken ? (
          <div className="inline-info">
            请先进入 <Link to="/admin/login">管理员登录</Link>。
          </div>
        ) : null}

        <div className="admin-metrics-grid">
          <article className="stat-card">
            <span>邀请码总数</span>
            <strong>{overview.inviteCount}</strong>
            <small>{overview.activeCount} 个正在启用</small>
          </article>
          <article className="stat-card">
            <span>调用次数控制</span>
            <strong>
              {overview.usageCount} / {overview.usageLimit}
            </strong>
            <small>跨邀请码总调用额度</small>
          </article>
          <article className="stat-card">
            <span>用户账号</span>
            <strong>{overview.userCount}</strong>
            <small>普通用户不展示管理员入口</small>
          </article>
          <article className="stat-card">
            <span>历史对话</span>
            <strong>{overview.runCount}</strong>
            <small>保留用户诊断会话记录</small>
          </article>
          <article className="stat-card">
            <span>演示数据</span>
            <strong>{overview.datasetCount}</strong>
            <small>专业案例与客户导入样本</small>
          </article>
        </div>
      </section>

          <section id="admin-datasets" className="panel admin-panel">
        <div className="panel-header">
          <div>
            <div className="section-kicker">Datasets</div>
            <h2>演示数据管理</h2>
          </div>
        </div>

        <p className="muted">维护客户侧可选择的专业演示数据，支持 CSV/JSON 录入，并预留按手机号与时间范围从物联网平台抽取。</p>

        <form className="record-form invite-admin-form" onSubmit={handleCreateDataset}>
          <label>
            <span>标题</span>
            <input
              className="input"
              aria-label="演示数据标题"
              value={datasetTitle}
              onChange={(event) => setDatasetTitle(event.target.value)}
              disabled={!adminToken || loading}
            />
          </label>
          <label>
            <span>诊断类型</span>
            <input
              className="input"
              aria-label="演示数据诊断类型"
              value={datasetProblemType}
              onChange={(event) => setDatasetProblemType(event.target.value)}
              disabled={!adminToken || loading}
            />
          </label>
          <label>
            <span>容量区间</span>
            <input
              className="input"
              aria-label="演示数据容量区间"
              value={datasetCapacityRange}
              onChange={(event) => setDatasetCapacityRange(event.target.value)}
              disabled={!adminToken || loading}
            />
          </label>
          <label>
            <span>说明</span>
            <input
              className="input"
              aria-label="演示数据说明"
              value={datasetDescription}
              onChange={(event) => setDatasetDescription(event.target.value)}
              disabled={!adminToken || loading}
            />
          </label>
          <label className="wide-field">
            <span>CSV 或 JSON 内容</span>
            <textarea
              className="input"
              aria-label="演示数据内容"
              value={datasetContent}
              onChange={(event) => setDatasetContent(event.target.value)}
              placeholder='{"time_offset_min":[0,10],"voltage_series":[46.1,47.0],"current_series":[10,9.6],"power_series":[461,451]}'
              disabled={!adminToken || loading}
            />
          </label>
          <button className="button primary" type="submit" disabled={!adminToken || loading || !datasetTitle.trim()}>
            新增演示数据
          </button>
        </form>

        <div className="record-form invite-admin-form">
          <label>
            <span>用户手机号</span>
            <input
              className="input"
              value={mysqlPhone}
              onChange={(event) => setMysqlPhone(event.target.value)}
              placeholder="13800000000"
              disabled={!adminToken || loading}
            />
          </label>
          <label>
            <span>开始时间</span>
            <input
              className="input"
              value={mysqlStartTime}
              onChange={(event) => setMysqlStartTime(event.target.value)}
              placeholder="2026-04-18T00:00:00"
              disabled={!adminToken || loading}
            />
          </label>
          <label>
            <span>结束时间</span>
            <input
              className="input"
              value={mysqlEndTime}
              onChange={(event) => setMysqlEndTime(event.target.value)}
              placeholder="2026-04-18T23:59:59"
              disabled={!adminToken || loading}
            />
          </label>
          <button className="button secondary" type="button" onClick={() => void handleMysqlImport()} disabled={!adminToken || loading}>
            从平台抽取数据
          </button>
        </div>

        <div className="table-list admin-data-list">
          {datasets.map((dataset) => (
            <article className="record-card admin-data-row" key={dataset.id}>
              <div>
                <strong>{dataset.name}</strong>
                <div className="muted small">{dataset.shortSummary}</div>
              </div>
              <div className="muted small">类型：{dataset.label}</div>
              <div className="muted small">容量：{dataset.capacityRange}</div>
              <div className={`status-pill ${dataset.isActive ? 'success' : 'danger'}`}>
                {dataset.isActive ? '启用' : '停用'}
              </div>
              <div className="record-actions">
                <button
                  className="button secondary"
                  type="button"
                  onClick={() => void handleToggleDataset(dataset)}
                  disabled={!adminToken || loading}
                >
                  {dataset.isActive ? '停用' : '启用'}
                </button>
                <button
                  className="button secondary"
                  type="button"
                  onClick={() => void handleDeleteDataset(dataset)}
                  disabled={!adminToken || loading}
                >
                  删除数据
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>

          <section id="admin-invites" className="panel admin-panel">
        <div className="panel-header">
          <div>
            <div className="section-kicker">Invite Control</div>
            <h2>邀请码管理</h2>
          </div>
        </div>

        <p className="muted">管理员可以为每个邀请码设置总调用次数、单用户调用次数，并随时启用、停用或删除。</p>

        {message ? <div className="inline-info">{message}</div> : null}

        <form className="record-form invite-admin-form" onSubmit={handleCreate}>
          <label>
            <span>邀请码名称</span>
            <input
              className="input"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="邀请码名称"
              disabled={!adminToken || loading}
            />
          </label>
          <label>
            <span>邀请码</span>
            <input
              className="input"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              placeholder="邀请码，可留空自动生成"
              disabled={!adminToken || loading}
            />
          </label>
          <label>
            <span>总调用次数</span>
            <input
              className="input"
              type="number"
              min={1}
              value={maxUses}
              onChange={(event) => setMaxUses(Number(event.target.value))}
              disabled={!adminToken || loading}
            />
          </label>
          <label>
            <span>单用户次数</span>
            <input
              className="input"
              type="number"
              min={1}
              value={perUserQuota}
              onChange={(event) => setPerUserQuota(Number(event.target.value))}
              disabled={!adminToken || loading}
            />
          </label>
          <button className="button primary" type="submit" disabled={!adminToken || loading || !name.trim()}>
            创建邀请码
          </button>
        </form>

        <div className="table-list invite-table">
          {loading && invites.length === 0 ? <div className="empty-state">正在读取邀请码。</div> : null}
          {!loading && invites.length === 0 ? <div className="empty-state">暂无邀请码。</div> : null}
          {invites.map((item) => {
            const draft = drafts[item.id] || toInviteDraft(item)
            const remaining = Math.max(draft.usageLimit - item.usageCount, 0)
            return (
              <article key={item.id} className="record-card invite-row" aria-label={`邀请码 ${item.code} 管理`}>
                <div className="record-card-head">
                  <strong>{item.code}</strong>
                  <span className={`status-pill ${item.status === 'active' ? 'success' : 'danger'}`}>
                    {item.status === 'active' ? '激活' : '停用'}
                  </span>
                </div>
                <div className="invite-edit-grid">
                  <label>
                    <span>名称</span>
                    <input
                      className="input"
                      aria-label={`${item.code} 名称`}
                      value={draft.name}
                      onChange={(event) => updateDraft(item.id, { name: event.target.value })}
                      disabled={!adminToken || loading}
                    />
                  </label>
                  <label>
                    <span>总调用次数</span>
                    <input
                      className="input"
                      type="number"
                      min={1}
                      aria-label={`${item.code} 总调用次数`}
                      value={draft.usageLimit}
                      onChange={(event) => updateDraft(item.id, { usageLimit: Number(event.target.value) })}
                      disabled={!adminToken || loading}
                    />
                  </label>
                  <label>
                    <span>单用户调用次数</span>
                    <input
                      className="input"
                      type="number"
                      min={1}
                      aria-label={`${item.code} 单用户调用次数`}
                      value={draft.perUserQuota}
                      onChange={(event) => updateDraft(item.id, { perUserQuota: Number(event.target.value) })}
                      disabled={!adminToken || loading}
                    />
                  </label>
                  <label>
                    <span>状态</span>
                    <select
                      className="input"
                      aria-label={`${item.code} 状态`}
                      value={draft.status}
                      onChange={(event) => updateDraft(item.id, { status: event.target.value as AdminInviteRow['status'] })}
                      disabled={!adminToken || loading}
                    >
                      <option value="active">启用</option>
                      <option value="paused">停用</option>
                    </select>
                  </label>
                </div>
                <div className="invite-quota-line">
                  <span>已用 {item.usageCount}</span>
                  <span>剩余 {remaining}</span>
                  <span>过期 {item.expiresAt}</span>
                </div>
                <div className="invite-progress" aria-label={`${item.code} 调用进度`}>
                  <span style={{ width: `${Math.min((item.usageCount / Math.max(draft.usageLimit, 1)) * 100, 100)}%` }} />
                </div>
                <div className="record-actions">
                  <button
                    className="button primary"
                    type="button"
                    onClick={() => void handleUpdate(item)}
                    disabled={!adminToken || loading}
                  >
                    保存修改 {item.code}
                  </button>
                  <button
                    className="button secondary"
                    type="button"
                    onClick={() => void handleDelete(item)}
                    disabled={!adminToken || loading}
                  >
                    删除
                  </button>
                </div>
              </article>
            )
          })}
        </div>
      </section>

          <section id="admin-users" className="panel admin-panel">
        <div className="panel-header">
          <div>
            <div className="section-kicker">Users</div>
            <h2>用户与配额</h2>
          </div>
        </div>
        <div className="table-list admin-data-list">
          {users.map((user) => (
            <article className="record-card admin-data-row" key={user.phone}>
              <div>
                <strong>{user.nickname}</strong>
                <div className="muted small">{user.phone}</div>
              </div>
              <div className="muted small">邀请码：{user.inviteCode}</div>
              <div className="muted small">
                配额：{user.quotaUsed} / {user.quotaTotal}
              </div>
              <div className="muted small">最近访问：{user.lastSeen}</div>
            </article>
          ))}
        </div>
      </section>

          <section id="admin-conversations" className="panel admin-panel">
        <div className="panel-header">
          <div>
            <div className="section-kicker">Conversations</div>
            <h2>用户历史对话记录</h2>
          </div>
        </div>
        <div className="table-list admin-data-list">
          {runs.map((run) => (
            <article className="record-card admin-data-row" key={run.id}>
              <div>
                <strong>{run.batteryId}</strong>
                <div className="muted small">{run.phone}</div>
              </div>
              <div className="muted small">诊断：{run.label}</div>
              <div className="muted small">
                容量区间：{run.capacityRange[0]} - {run.capacityRange[1]} Ah
              </div>
              <div className={`status-pill ${run.status === 'success' ? 'success' : 'danger'}`}>
                {run.status === 'success' ? '完成' : '失败'}
              </div>
              <div className="muted small">{run.createdAt}</div>
            </article>
          ))}
        </div>
      </section>
        </main>
      </section>
    </div>
  )
}

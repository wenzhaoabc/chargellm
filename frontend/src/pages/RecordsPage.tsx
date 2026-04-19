import type { FormEvent } from 'react'
import { useState } from 'react'
import { queryChargingRecordsByPhoneMock } from '@/api/charge'

export function RecordsPage() {
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [result, setResult] = useState<ReturnType<typeof queryChargingRecordsByPhoneMock> | null>(null)

  const handleQuery = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setResult(queryChargingRecordsByPhoneMock(phone))
  }

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="panel-header">
          <div>
            <div className="section-kicker">我的充电记录</div>
            <h2>手机号验证码登录后查询真实历史记录</h2>
          </div>
          <span className="status-pill warning">mock UI</span>
        </div>
        <p className="muted">
          这个页面先保留真实业务入口，后续接入短信验证码和数据库查询即可。示例体验不需要手机号。
        </p>

        <form className="record-form" onSubmit={handleQuery}>
          <input
            className="input"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            placeholder="手机号"
          />
          <input
            className="input"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder="验证码"
          />
          <button className="button secondary" type="submit">
            查询历史记录
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <div className="section-kicker">查询结果</div>
            <h2>待接入真实数据源</h2>
          </div>
        </div>

        {result ? (
          <div className="record-list">
            <div className="inline-info">
              手机号：<strong>{result.phone}</strong>
            </div>
            {result.items.map((item) => (
              <article key={item.recordId} className="record-card">
                <div className="record-card-head">
                  <strong>{item.batteryId}</strong>
                  <span className="status-pill success">{item.status}</span>
                </div>
                <div className="muted small">最近充电：{item.lastChargeAt}</div>
                <div className="muted small">记录编号：{item.recordId}</div>
              </article>
            ))}
            <p className="muted small">{result.message}</p>
          </div>
        ) : (
          <div className="empty-state">提交手机号和验证码后，这里展示真实历史记录。</div>
        )}
      </section>
    </div>
  )
}

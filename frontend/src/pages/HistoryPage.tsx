import { listConversationHistory } from '@/api/conversations'

export function HistoryPage() {
  const history = listConversationHistory()

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="panel-header">
          <div>
            <div className="section-kicker">诊断历史</div>
            <h2>最近的分析记录</h2>
          </div>
          <span className="muted small">{history.length} 条对话</span>
        </div>

        <div className="record-list">
          {history.length === 0 ? <div className="empty-state">暂无诊断对话记录。</div> : null}
          {history.map((conversation) => (
            <article key={conversation.id} className="record-card conversation-record-card">
              <div className="record-card-head">
                <strong>{conversation.title}</strong>
                <span className="status-pill success">已保存</span>
              </div>
              <div className="muted small">时间：{conversation.updatedAt || conversation.createdAt}</div>
              {conversation.turns.map((turn) => (
                <div key={turn.id} className="conversation-turn-summary">
                  <div className="muted small">
                    {turn.batteryName} · {turn.batteryLabel}
                  </div>
                  <p>{turn.question}</p>
                  <div className="tag-row">
                    <span>{turn.diagnosis.label}</span>
                    <span>{turn.diagnosis.capacityRange}</span>
                    <span>{Math.round(turn.diagnosis.confidence * 100)}%</span>
                  </div>
                  <p className="muted small">{turn.answer || turn.diagnosis.reason}</p>
                </div>
              ))}
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

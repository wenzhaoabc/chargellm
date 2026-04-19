import type { ChatEvent, DiagnosisResult } from '@/api/types'

type Props = {
  events: ChatEvent[]
  finalResult: DiagnosisResult | null
  pending: boolean
}

export function StreamConsole({ events, finalResult, pending }: Props) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <div className="section-kicker">SSE 预览</div>
          <h2>聊天流式输出</h2>
        </div>
        <span className={`status-pill ${pending ? 'warning' : 'success'}`}>
          {pending ? '流式进行中' : '已完成'}
        </span>
      </div>

      {events.length === 0 ? (
        <div className="empty-state">输入问题后，这里会逐步展示状态、工具结果和模型输出。</div>
      ) : (
        <details className="thought-panel stream-details">
          <summary>{pending ? '正在流式执行' : '流式执行过程'} · {events.length} 条事件</summary>
          <div className="stream-list">
            {events.map((event, index) => (
              <div key={`${event.type}-${index}`} className="stream-item">
                <span className={`stream-type ${event.type}`}>{event.type}</span>
                <div>
                  <div className="stream-message">{event.message}</div>
                  {event.payload ? <pre className="stream-payload">{JSON.stringify(event.payload, null, 2)}</pre> : null}
                </div>
              </div>
            ))}
          </div>
        </details>
      )}

      {finalResult ? (
        <div className="stream-final">
          <div className="diagnosis-row">
            <div>
              <div className="muted small">预测标签</div>
              <strong>{finalResult.label}</strong>
            </div>
            <div>
              <div className="muted small">容量区间</div>
              <strong>{finalResult.capacityRange}</strong>
            </div>
            <div>
              <div className="muted small">置信度</div>
              <strong>{Math.round(finalResult.confidence * 100)}%</strong>
            </div>
          </div>
          <p>{finalResult.reason}</p>
          <div className="tag-row">
            {finalResult.keyProcesses.map((item) => (
              <span key={item} className="tag">
                {item}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  )
}

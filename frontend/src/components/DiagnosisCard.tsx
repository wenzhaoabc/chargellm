import type { DiagnosisResult } from '@/api/types'

type Props = {
  result: DiagnosisResult | null
  batteryId: string
}

export function DiagnosisCard({ result, batteryId }: Props) {
  return (
    <section className="panel diagnosis-card">
      <div className="panel-header">
        <div>
          <div className="section-kicker">诊断卡片</div>
          <h2>当前推理结果</h2>
        </div>
        <span className="muted small">{batteryId}</span>
      </div>

      {result ? (
        <>
          <div className="diagnosis-grid">
            <div>
              <div className="muted small">标签</div>
              <div className="value">{result.label}</div>
            </div>
            <div>
              <div className="muted small">容量区间</div>
              <div className="value">{result.capacityRange}</div>
            </div>
            <div>
              <div className="muted small">置信度</div>
              <div className="value">{Math.round(result.confidence * 100)}%</div>
            </div>
          </div>
          <p className="diagnosis-reason">{result.reason}</p>
          <div className="tag-row">
            {result.keyProcesses.length > 0 ? (
              result.keyProcesses.map((id) => (
                <span key={id} className="tag">
                  {id}
                </span>
              ))
            ) : (
              <span className="muted small">暂无关键过程</span>
            )}
          </div>
        </>
      ) : (
        <div className="empty-state">诊断结果会在 SSE 流完成后显示在这里。</div>
      )}
    </section>
  )
}

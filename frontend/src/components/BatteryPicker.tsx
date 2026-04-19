import type { BatteryExample } from '@/api/types'

type Props = {
  batteries: BatteryExample[]
  selectedId: string
  onSelect: (batteryId: string) => void
}

export function BatteryPicker({ batteries, selectedId, onSelect }: Props) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <div className="section-kicker">示例电池</div>
          <h2>选择一块电池开始体验</h2>
        </div>
        <span className="muted small">{batteries.length} 个样本</span>
      </div>

      <div className="battery-grid">
        {batteries.map((battery) => {
          const active = battery.id === selectedId
          return (
            <button
              key={battery.id}
              type="button"
              className={`battery-card${active ? ' active' : ''}`}
              onClick={() => onSelect(battery.id)}
            >
              <div className="battery-card-head">
                <strong>{battery.name}</strong>
                <span className={`status-pill ${battery.status}`}>{battery.label}</span>
              </div>
              <p>{battery.shortSummary}</p>
              <div className="battery-card-meta">
                <span>过程 {battery.processCount}</span>
                <span>容量 {battery.capacityRange}</span>
              </div>
            </button>
          )
        })}
      </div>
    </section>
  )
}

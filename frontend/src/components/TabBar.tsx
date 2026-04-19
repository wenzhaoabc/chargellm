type TabItem = {
  key: string
  label: string
}

type Props = {
  tabs: TabItem[]
  activeKey: string
  onChange: (key: string) => void
}

export function TabBar({ tabs, activeKey, onChange }: Props) {
  return (
    <div className="tab-bar">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          className={`tab-button${tab.key === activeKey ? ' active' : ''}`}
          onClick={() => onChange(tab.key)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}

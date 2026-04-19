import { useMemo } from 'react'
import type { BatteryExample, ChargingProcess } from '@/api/types'

type Props = {
  battery: BatteryExample
  process: ChargingProcess
}

type Point = [number, number]

const WIDTH = 720
const HEIGHT = 320
const PAD = { left: 56, right: 28, top: 76, bottom: 42 }

function extent(values: number[]) {
  const finite = values.filter(Number.isFinite)
  if (!finite.length) {
    return [0, 1] as const
  }
  const min = Math.min(...finite)
  const max = Math.max(...finite)
  return min === max ? [min - 1, max + 1] as const : [min, max] as const
}

function toPoints(time: number[], values: number[]): Point[] {
  const count = Math.min(time.length, values.length)
  return Array.from({ length: count }, (_, index) => [time[index], values[index]])
}

function project(points: Point[], xExtent: readonly [number, number], yExtent: readonly [number, number]) {
  const innerWidth = WIDTH - PAD.left - PAD.right
  const innerHeight = HEIGHT - PAD.top - PAD.bottom
  const [minX, maxX] = xExtent
  const [minY, maxY] = yExtent

  return points.map(([x, y]) => {
    const px = PAD.left + ((x - minX) / (maxX - minX || 1)) * innerWidth
    const py = PAD.top + innerHeight - ((y - minY) / (maxY - minY || 1)) * innerHeight
    return [Number(px.toFixed(2)), Number(py.toFixed(2))] as Point
  })
}

function pathFrom(points: Point[]) {
  return points.map(([x, y], index) => `${index === 0 ? 'M' : 'L'} ${x} ${y}`).join(' ')
}

function axisTicks(min: number, max: number, count: number) {
  return Array.from({ length: count }, (_, index) => {
    const value = min + ((max - min) * index) / Math.max(count - 1, 1)
    return Number(value.toFixed(1))
  })
}

export function ChargeChart({ battery, process }: Props) {
  const chart = useMemo(() => {
    const time = process.timeOffsetMin
    const currentPoints = toPoints(time, process.current)
    const powerPoints = toPoints(time, process.power)
    const xExtent = extent(time)
    const currentExtent = extent(process.current)
    const powerExtent = extent(process.power)

    return {
      currentPath: pathFrom(project(currentPoints, xExtent, currentExtent)),
      powerPath: pathFrom(project(powerPoints, xExtent, powerExtent)),
      currentDots: project(currentPoints, xExtent, currentExtent),
      powerDots: project(powerPoints, xExtent, powerExtent),
      xTicks: axisTicks(xExtent[0], xExtent[1], 5),
      currentTicks: axisTicks(currentExtent[0], currentExtent[1], 4),
      powerTicks: axisTicks(powerExtent[0], powerExtent[1], 4),
      xExtent,
    }
  }, [process])

  const innerHeight = HEIGHT - PAD.top - PAD.bottom
  const innerWidth = WIDTH - PAD.left - PAD.right

  return (
    <svg
      className="chart-box native-chart"
      data-testid="charge-chart"
      role="img"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      aria-label={`${battery.name} ${process.title} 充电曲线`}
    >
      <title>{`${battery.name} ${process.title} 充电曲线`}</title>
      <desc>{process.note || battery.longSummary}</desc>

      <text x="20" y="28" className="chart-title">{`${battery.name} · ${process.title}`}</text>
      <text x="20" y="50" className="chart-subtitle">
        {process.note || battery.longSummary}
      </text>

      <g className="chart-grid">
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const y = PAD.top + innerHeight * ratio
          return <line key={ratio} x1={PAD.left} x2={PAD.left + innerWidth} y1={y} y2={y} />
        })}
      </g>

      <line className="chart-axis" x1={PAD.left} x2={PAD.left + innerWidth} y1={PAD.top + innerHeight} y2={PAD.top + innerHeight} />
      <line className="chart-axis" x1={PAD.left} x2={PAD.left} y1={PAD.top} y2={PAD.top + innerHeight} />

      {chart.xTicks.map((tick) => {
        const x = PAD.left + ((tick - chart.xExtent[0]) / (chart.xExtent[1] - chart.xExtent[0] || 1)) * innerWidth
        return (
          <g key={tick}>
            <line className="chart-tick" x1={x} x2={x} y1={PAD.top + innerHeight} y2={PAD.top + innerHeight + 5} />
            <text className="chart-label" x={x} y={PAD.top + innerHeight + 22} textAnchor="middle">
              {tick}
            </text>
          </g>
        )
      })}

      <text className="chart-label" x={PAD.left + innerWidth / 2} y={HEIGHT - 6} textAnchor="middle">
        采集时间 / min
      </text>

      <path className="chart-line current" d={chart.currentPath} />
      <path className="chart-line power" d={chart.powerPath} />

      {chart.currentDots.map(([x, y], index) => (
        <circle key={`current-${index}`} className="chart-dot current" cx={x} cy={y} r="3" />
      ))}
      {chart.powerDots.map(([x, y], index) => (
        <circle key={`power-${index}`} className="chart-dot power" cx={x} cy={y} r="3" />
      ))}

      <g className="chart-legend">
        <circle className="chart-dot current" cx="532" cy="25" r="4" />
        <text x="544" y="29">电流</text>
        <circle className="chart-dot power" cx="604" cy="25" r="4" />
        <text x="616" y="29">功率</text>
      </g>

      <g className="chart-scale current-scale">
        {chart.currentTicks.map((tick, index) => (
          <text key={`current-tick-${index}`} x="16" y={PAD.top + innerHeight - (innerHeight * index) / 3 + 4}>
            {tick}
          </text>
        ))}
      </g>
      <g className="chart-scale power-scale">
        {chart.powerTicks.map((tick, index) => (
          <text key={`power-tick-${index}`} x={WIDTH - 24} y={PAD.top + innerHeight - (innerHeight * index) / 3 + 4} textAnchor="end">
            {tick}
          </text>
        ))}
      </g>
    </svg>
  )
}

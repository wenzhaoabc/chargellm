import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { ChargeOrder } from '@/api/chargeOrders'

export type ChargeHighlight = {
  metric: 'power' | 'voltage' | 'current'
  start_min: number
  end_min: number
  reason?: string
  severity?: 'info' | 'warning' | 'danger'
}

const SEVERITY_COLOR: Record<NonNullable<ChargeHighlight['severity']>, string> = {
  info: 'rgba(24, 144, 255, 0.18)',
  warning: 'rgba(250, 173, 20, 0.22)',
  danger: 'rgba(255, 77, 79, 0.25)',
}

const METRIC_NAMES: Record<ChargeHighlight['metric'], string> = {
  power: '功率 (W)',
  voltage: '电压 (V)',
  current: '电流 (A)',
}

type Props = {
  order: ChargeOrder
  highlights?: ChargeHighlight[]
  height?: number
  compact?: boolean
}

export function ChargeChartECharts({ order, highlights = [], height = 280, compact = false }: Props) {
  const option = useMemo(() => buildOption(order, highlights, compact), [order, highlights, compact])
  return <ReactECharts option={option} style={{ height, width: '100%' }} notMerge />
}

function pairs(times: number[], values: (number | null)[]): [number, number][] {
  const out: [number, number][] = []
  for (let i = 0; i < times.length && i < values.length; i += 1) {
    const v = values[i]
    if (v !== null && v !== undefined && Number.isFinite(v)) {
      out.push([times[i], v])
    }
  }
  return out
}

function buildOption(order: ChargeOrder, highlights: ChargeHighlight[], compact: boolean) {
  const { time_offset_min, powers, voltages, currents } = order.series
  const series = [
    {
      name: METRIC_NAMES.power,
      type: 'line',
      smooth: true,
      yAxisIndex: 0,
      symbol: 'circle',
      symbolSize: compact ? 3 : 5,
      data: pairs(time_offset_min, powers),
      lineStyle: { width: 2, color: '#1677ff' },
      itemStyle: { color: '#1677ff' },
      markArea: buildMarkArea(highlights, 'power'),
    },
    {
      name: METRIC_NAMES.voltage,
      type: 'line',
      smooth: true,
      yAxisIndex: 1,
      symbol: 'circle',
      symbolSize: compact ? 3 : 5,
      data: pairs(time_offset_min, voltages),
      lineStyle: { width: 2, color: '#52c41a' },
      itemStyle: { color: '#52c41a' },
      markArea: buildMarkArea(highlights, 'voltage'),
    },
    {
      name: METRIC_NAMES.current,
      type: 'line',
      smooth: true,
      yAxisIndex: 2,
      symbol: 'circle',
      symbolSize: compact ? 3 : 5,
      data: pairs(time_offset_min, currents),
      lineStyle: { width: 2, color: '#fa8c16' },
      itemStyle: { color: '#fa8c16' },
      markArea: buildMarkArea(highlights, 'current'),
    },
  ]
  return {
    grid: { left: 50, right: 60, top: compact ? 28 : 48, bottom: 36 },
    legend: {
      top: compact ? 0 : 10,
      icon: 'roundRect',
      itemWidth: 14,
      textStyle: { fontSize: compact ? 11 : 12 },
    },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'value',
      name: '充电时长 (min)',
      nameLocation: 'middle',
      nameGap: 22,
      axisLine: { lineStyle: { color: '#d9d9d9' } },
    },
    yAxis: [
      { type: 'value', name: '功率', position: 'left', axisLine: { show: false }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
      { type: 'value', name: '电压', position: 'right', axisLine: { show: false }, splitLine: { show: false } },
      { type: 'value', name: '电流', position: 'right', offset: 50, axisLine: { show: false }, splitLine: { show: false } },
    ],
    series,
  }
}

function buildMarkArea(highlights: ChargeHighlight[], metric: ChargeHighlight['metric']) {
  const matching = highlights.filter((h) => h.metric === metric)
  if (matching.length === 0) return undefined
  return {
    silent: false,
    itemStyle: { color: SEVERITY_COLOR[matching[0].severity || 'warning'] },
    data: matching.map((h) => [
      {
        xAxis: h.start_min,
        name: h.reason || '异常区间',
        itemStyle: { color: SEVERITY_COLOR[h.severity || 'warning'] },
      },
      { xAxis: h.end_min },
    ]),
  }
}

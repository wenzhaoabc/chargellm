import { render, screen } from '@testing-library/react'
import { listExampleBatteries } from '@/api/charge'
import { ChargeChart } from './ChargeChart'

describe('ChargeChart', () => {
  it('renders charging curves with native svg without chart dependencies', () => {
    const battery = listExampleBatteries()[0]
    const process = battery.processes[0]

    render(<ChargeChart battery={battery} process={process} />)

    expect(screen.getByTestId('charge-chart')).toBeInstanceOf(SVGSVGElement)
    expect(screen.getByText(`${battery.name} · ${process.title}`)).toBeInTheDocument()
    expect(screen.getByText('电流')).toBeInTheDocument()
    expect(screen.getByText('功率')).toBeInTheDocument()
  })
})

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { InviteGate } from '@/components/InviteGate'

const technologySteps = [
  '以海量专家诊断样本训练电池健康识别能力，沉淀老化、故障和异常充电知识。',
  '时序模型理解每一次充电过程中的电压、电流、功率和容量变化。',
  '电池画像模块聚合跨周期充电历史，形成可解释的健康状态表征。',
  '大模型结合专家知识与曲线证据，输出诊断标签、置信度、关键过程和解释。',
]

const capabilityCards = [
  {
    title: '老化趋势识别',
    text: '识别容量衰减、充电时间拉长、功率响应变弱等慢变量变化。',
  },
  {
    title: '故障过程定位',
    text: '定位异常波动、突变、非平滑曲线和疑似风险充电片段。',
  },
  {
    title: '结构化诊断报告',
    text: '输出可落库、可审计、可追溯的 JSON 诊断结论和关键证据。',
  },
  {
    title: '对话式解释',
    text: '用户可以围绕一块电池连续追问，查看模型推理过程和曲线依据。',
  },
]

const scenarioCards = [
  {
    title: '政府监管单位',
    text: '用于区域充电安全监测、异常电池预警、监管抽检和风险闭环管理。',
  },
  {
    title: '充电桩运营商',
    text: '用于站点运营质量评估、异常充电订单复核、用户投诉辅助分析。',
  },
  {
    title: '个人用户',
    text: '用于了解电池健康状态、识别老化风险、获得易懂的充电建议。',
  },
]

const architectureNodes = ['充电历史数据', '时序特征编码', '电池画像聚合', '大模型推理', '诊断结论']

export function LandingPage() {
  const navigate = useNavigate()
  const [inviteOpen, setInviteOpen] = useState(false)

  return (
    <main className="landing-page">
      <header className="landing-topbar">
        <Link className="landing-brand" to="/">
          <span>CL</span>
          ChargeLLM
        </Link>
      </header>

      <section className="landing-hero">
        <div className="landing-copy">
          <span className="eyebrow">E-bike Battery Health Model</span>
          <h1>电动自行车电池健康诊断大模型</h1>
          <p>
            基于海量专家标注数据训练，ChargeLLM 面向电动自行车电池的充电历史、容量衰减、
            功率响应和异常曲线进行综合推理，形成可解释的健康诊断、老化识别和风险预警能力。
          </p>
          <div className={`landing-actions ${inviteOpen ? 'open' : ''}`}>
            <button className="experience-button" type="button" onClick={() => setInviteOpen((open) => !open)}>
              立即体验
            </button>
            {inviteOpen ? (
              <div className="landing-inline-invite" role="group" aria-label="邀请码体验入口">
                <InviteGate onConfirmed={() => navigate('/chat')} />
              </div>
            ) : null}
            <a href="mailto:contact@chargellm.local">联系团队获取试用邀请码</a>
          </div>
        </div>

        <div className="landing-preview" aria-label="产品能力预览">
          <div className="preview-window">
            <div className="preview-line user">请判断这块电池是否存在老化或故障风险。</div>
            <div className="preview-line assistant">正在比对专家样本，识别充电曲线与容量衰减特征。</div>
            <div className="preview-result">
              <span>最终诊断</span>
              <strong>电池老化 · 置信度 87%</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-section tech-section" aria-label="技术原理介绍">
        <div className="section-title">
          <span className="eyebrow">How it works</span>
          <h2>技术原理</h2>
          <p>从原始充电曲线到可解释诊断结论，ChargeLLM 采用时序模型与大语言模型协同推理。</p>
        </div>
        <div className="technology-grid">
          {technologySteps.map((step, index) => (
            <article key={step}>
              <span>{String(index + 1).padStart(2, '0')}</span>
              <p>{step}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section architecture-section" aria-label="模型运作架构图">
        <div className="section-title">
          <span className="eyebrow">Model Flow</span>
          <h2>模型运作架构</h2>
          <p>仅展示客户理解所需的高层链路，隐藏训练细节、权重结构和内部参数。</p>
        </div>
        <div className="architecture-flow">
          {architectureNodes.map((node, index) => (
            <div className="architecture-step" key={node}>
              <div className="architecture-node">{node}</div>
              {index < architectureNodes.length - 1 ? <div className="architecture-arrow">→</div> : null}
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section" aria-label="核心能力介绍">
        <div className="section-title">
          <span className="eyebrow">Capabilities</span>
          <h2>核心能力</h2>
          <p>围绕电池健康状态判断，覆盖风险发现、证据定位、结论输出和对话解释。</p>
        </div>
        <div className="capability-grid">
          {capabilityCards.map((card) => (
            <article key={card.title}>
              <h3>{card.title}</h3>
              <p>{card.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section scenario-section" aria-label="应用场景介绍">
        <div className="section-title">
          <span className="eyebrow">Scenarios</span>
          <h2>应用场景</h2>
          <p>面向公共监管、商业运营和个人用户，提供同一诊断能力的不同使用入口。</p>
        </div>
        <div className="scenario-grid">
          {scenarioCards.map((card) => (
            <article key={card.title}>
              <h3>{card.title}</h3>
              <p>{card.text}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  )
}

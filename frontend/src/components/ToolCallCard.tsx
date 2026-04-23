import { Alert, Card, Collapse, Descriptions, Space, Tag, Typography } from 'antd'
import { CheckCircleFilled, ExclamationCircleFilled, LoadingOutlined } from '@ant-design/icons'
import type { AgentEvent } from '@/api/agentChat'

export type ToolInvocation = {
  id: string
  name: string
  arguments: string
  result?: Extract<AgentEvent, { type: 'tool_result' }>
}

type Props = {
  invocation: ToolInvocation
}

/** Render a single tool call + its result inline within the assistant bubble. */
export function ToolCallCard({ invocation }: Props) {
  const { name, arguments: args, result } = invocation
  const argsParsed = safeJson(args)
  const pending = !result
  const failed = result?.is_error

  const header = (
    <Space size={8} wrap>
      {pending ? (
        <LoadingOutlined />
      ) : failed ? (
        <ExclamationCircleFilled style={{ color: '#ff4d4f' }} />
      ) : (
        <CheckCircleFilled style={{ color: '#52c41a' }} />
      )}
      <Typography.Text strong>{displayName(name)}</Typography.Text>
      {result?.display && <Tag color={failed ? 'red' : 'blue'}>{result.display}</Tag>}
    </Space>
  )

  return (
    <Card
      size="small"
      style={{ background: '#fafafa', border: '1px solid #eaeaea', marginBlock: 6 }}
      styles={{ body: { padding: 10 } }}
    >
      <Collapse
        ghost
        size="small"
        items={[
          {
            key: 'detail',
            label: header,
            children: (
              <Space direction="vertical" style={{ width: '100%' }} size={8}>
                {argsParsed && Object.keys(argsParsed).length > 0 && (
                  <Descriptions size="small" column={1} title="参数">
                    {Object.entries(argsParsed).map(([k, v]) => (
                      <Descriptions.Item key={k} label={k}>
                        <Typography.Text code style={{ fontSize: 12 }}>
                          {typeof v === 'string' ? v : JSON.stringify(v)}
                        </Typography.Text>
                      </Descriptions.Item>
                    ))}
                  </Descriptions>
                )}
                {pending && <Alert type="info" showIcon message="工具执行中…" />}
                {failed && (
                  <Alert
                    type="error"
                    showIcon
                    message="工具执行失败"
                    description={String((result?.data as { error?: unknown })?.error ?? '未知错误')}
                  />
                )}
              </Space>
            ),
          },
        ]}
      />
    </Card>
  )
}

function displayName(name: string) {
  switch (name) {
    case 'query_charging_records':
      return '🔍 查询充电记录'
    case 'highlight_charge_segment':
      return '🟡 标注异常时段'
    case 'compare_orders':
      return '📊 跨订单对比'
    case 'web_search':
      return '🌐 联网搜索'
    default:
      return name
  }
}

function safeJson(raw: string): Record<string, unknown> | null {
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

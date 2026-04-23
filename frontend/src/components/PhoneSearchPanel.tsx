import { useEffect, useState } from 'react'
import { App, Button, Card, Form, Input, List, Space, Tag, Typography } from 'antd'
import { SearchOutlined, SendOutlined } from '@ant-design/icons'
import { fetchChargeOrders, type ChargeOrder } from '@/api/chargeOrders'

type Props = {
  onUseOrders: (phone: string, orders: ChargeOrder[]) => void
}

const SEARCH_RESULT_KEY = 'chargellm.phoneSearch.result'

type PersistedResult = { phone: string; phoneMasked: string; orders: ChargeOrder[] }

function loadPersisted(): PersistedResult | null {
  if (typeof window === 'undefined') return null
  const raw = window.sessionStorage.getItem(SEARCH_RESULT_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as PersistedResult
  } catch {
    return null
  }
}

function savePersisted(result: PersistedResult | null) {
  if (typeof window === 'undefined') return
  if (result) {
    window.sessionStorage.setItem(SEARCH_RESULT_KEY, JSON.stringify(result))
  } else {
    window.sessionStorage.removeItem(SEARCH_RESULT_KEY)
  }
}

export function PhoneSearchPanel({ onUseOrders }: Props) {
  const { message } = App.useApp()
  const [form] = Form.useForm<{ phone: string }>()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<PersistedResult | null>(() => loadPersisted())

  useEffect(() => {
    if (result) {
      form.setFieldsValue({ phone: result.phone })
    }
    // Only run on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    savePersisted(result)
  }, [result])

  async function onSearch({ phone }: { phone: string }) {
    setLoading(true)
    try {
      const resp = await fetchChargeOrders(phone.trim())
      setResult({ phone: phone.trim(), phoneMasked: resp.phone_masked, orders: resp.orders })
      if (resp.orders.length === 0) {
        message.info('该手机号在最近 6 个月内没有充电记录')
      }
    } catch (err) {
      message.error(err instanceof Error ? err.message : '查询失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card
      size="small"
      title={<Space><SearchOutlined />用户充电记录查询</Space>}
      extra={result && <Tag color="blue">{result.phoneMasked}</Tag>}
    >
      <Form form={form} layout="vertical" onFinish={onSearch} style={{ marginBottom: 12 }}>
        <Form.Item
          name="phone"
          rules={[{ required: true, pattern: /^\d{6,20}$/, message: '请输入有效手机号' }]}
          style={{ marginBottom: 8 }}
        >
          <Input placeholder="输入手机号（如 13061947220）" allowClear />
        </Form.Item>
        <Form.Item style={{ marginBottom: 0 }}>
          <Button type="primary" htmlType="submit" loading={loading} icon={<SearchOutlined />} block>
            查询
          </Button>
        </Form.Item>
      </Form>
      {result && result.orders.length > 0 && (
        <>
          <Space direction="vertical" size={6} style={{ marginBottom: 8, width: '100%' }}>
            <Typography.Text type="secondary">
              共 {result.orders.length} 次充电记录
            </Typography.Text>
            <Button
              size="small"
              type="primary"
              icon={<SendOutlined />}
              onClick={() => onUseOrders(result.phone, result.orders)}
              block
            >
              将全部记录送入对话分析
            </Button>
          </Space>
          <List
            size="small"
            dataSource={result.orders}
            renderItem={(order) => (
              <List.Item>
                <Space direction="vertical" size={2} style={{ width: '100%' }}>
                  <Space wrap>
                    <Typography.Text strong>{order.order_no}</Typography.Text>
                    {order.supplier_name && <Tag>{order.supplier_name}</Tag>}
                    {order.charge_capacity !== null && (
                      <Tag color="purple">容量 {order.charge_capacity}</Tag>
                    )}
                  </Space>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {order.charge_start_time} → {order.charge_end_time} · {order.series.time_offset_min.length} 个数据点
                  </Typography.Text>
                </Space>
              </List.Item>
            )}
          />
        </>
      )}
    </Card>
  )
}

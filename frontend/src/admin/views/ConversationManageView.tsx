import { useCallback, useEffect, useState } from 'react'
import { App, Button, Drawer, Empty, Input, Space, Table, Tag, Typography } from 'antd'
import { getAdminConversation, listAdminConversations, type AdminConversation, type AdminConversationDetail } from '@/api/adminExtra'

export function ConversationManageView() {
  const { message } = App.useApp()
  const [items, setItems] = useState<AdminConversation[]>([])
  const [loading, setLoading] = useState(false)
  const [phoneFilter, setPhoneFilter] = useState('')
  const [detail, setDetail] = useState<AdminConversationDetail | null>(null)

  const reload = useCallback(async (phone?: string) => {
    setLoading(true)
    try {
      const res = await listAdminConversations({ phone, limit: 100 })
      setItems(res.items)
    } catch (err) {
      message.error('加载失败：' + (err instanceof Error ? err.message : '未知错误'))
    } finally {
      setLoading(false)
    }
  }, [message])

  useEffect(() => { reload() }, [reload])

  async function openDetail(id: number) {
    try {
      setDetail(await getAdminConversation(id))
    } catch (err) {
      message.error('详情加载失败：' + (err instanceof Error ? err.message : '未知错误'))
    }
  }

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>对话历史</Typography.Title>
        <Input
          placeholder="按手机号过滤"
          value={phoneFilter}
          allowClear
          onChange={(e) => setPhoneFilter(e.target.value)}
          onPressEnter={() => reload(phoneFilter || undefined)}
          style={{ width: 200 }}
        />
        <Button onClick={() => reload(phoneFilter || undefined)}>查询</Button>
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        size="small"
        pagination={{ pageSize: 30 }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          { title: '标题', dataIndex: 'title' },
          { title: '手机号', dataIndex: 'phone_masked', render: (v) => v || '-' },
          { title: '消息数', dataIndex: 'message_count', width: 90 },
          { title: '创建时间', dataIndex: 'created_at', render: (v: string) => new Date(v).toLocaleString('zh-CN') },
          {
            title: '操作',
            width: 100,
            render: (_, row) => <Button size="small" onClick={() => openDetail(row.id)}>查看</Button>,
          },
        ]}
      />
      <Drawer
        open={detail !== null}
        title={detail ? `对话 #${detail.id} · ${detail.title}` : ''}
        onClose={() => setDetail(null)}
        width={720}
      >
        {detail ? (
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            {detail.messages.map((m) => (
              <div key={m.id} style={{ padding: 10, borderRadius: 6, background: roleBg(m.role) }}>
                <Tag color={roleColor(m.role)}>{m.role}</Tag>
                <Typography.Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                  {new Date(m.created_at).toLocaleString('zh-CN')}
                </Typography.Text>
                <pre style={{ marginTop: 6, marginBottom: 0, whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{m.content}</pre>
                {m.metadata && (
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    工具: {String((m.metadata as { name?: string }).name || '-')}
                  </Typography.Text>
                )}
              </div>
            ))}
          </Space>
        ) : (
          <Empty />
        )}
      </Drawer>
    </div>
  )
}

function roleColor(role: string) {
  if (role === 'user') return 'blue'
  if (role === 'assistant') return 'green'
  if (role === 'tool') return 'orange'
  return 'default'
}

function roleBg(role: string) {
  if (role === 'user') return '#f0f7ff'
  if (role === 'assistant') return '#f6ffed'
  if (role === 'tool') return '#fff7e6'
  return '#fafafa'
}

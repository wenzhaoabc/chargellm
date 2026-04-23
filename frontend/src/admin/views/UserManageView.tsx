import { useCallback, useEffect, useState } from 'react'
import { App, Button, InputNumber, Space, Switch, Table, Tag, Typography } from 'antd'
import { listAdminUsersBackend, updateAdminUser, type AdminUser } from '@/api/adminExtra'

export function UserManageView() {
  const { message } = App.useApp()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(false)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const res = await listAdminUsersBackend({ limit: 200 })
      setUsers(res.items)
    } catch (err) {
      message.error('加载失败：' + (err instanceof Error ? err.message : '未知错误'))
    } finally {
      setLoading(false)
    }
  }, [message])

  useEffect(() => {
    reload()
  }, [reload])

  async function toggleActive(id: number, value: boolean) {
    try {
      await updateAdminUser(id, { is_active: value })
      message.success(value ? '已启用' : '已禁用')
      reload()
    } catch (err) {
      message.error('更新失败：' + (err instanceof Error ? err.message : '未知错误'))
    }
  }

  async function setQuota(id: number, value: number) {
    try {
      await updateAdminUser(id, { usage_quota_total: value })
      message.success('配额已更新')
      reload()
    } catch (err) {
      message.error('更新失败：' + (err instanceof Error ? err.message : '未知错误'))
    }
  }

  return (
    <div>
      <Typography.Title level={4}>用户管理</Typography.Title>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={users}
        size="small"
        pagination={{ pageSize: 20 }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          { title: '手机号', dataIndex: 'phone_masked', render: (v) => v || <Typography.Text type="secondary">未绑定</Typography.Text> },
          { title: '用户名', dataIndex: 'username', render: (v) => v || '-' },
          { title: '角色', dataIndex: 'role', render: (v) => <Tag color={v === 'admin' ? 'gold' : 'blue'}>{v}</Tag> },
          {
            title: '配额',
            render: (_, row) => (
              <Space>
                <Typography.Text>{row.usage_quota_used} /</Typography.Text>
                <InputNumber
                  size="small"
                  min={0}
                  defaultValue={row.usage_quota_total}
                  onPressEnter={(e) => setQuota(row.id, Number((e.target as HTMLInputElement).value))}
                  onBlur={(e) => {
                    const next = Number((e.target as HTMLInputElement).value)
                    if (next !== row.usage_quota_total) setQuota(row.id, next)
                  }}
                />
              </Space>
            ),
          },
          {
            title: '启用',
            dataIndex: 'is_active',
            width: 80,
            render: (v: boolean, row) => (
              <Switch checked={v} onChange={(checked) => toggleActive(row.id, checked)} size="small" />
            ),
          },
          { title: '注册时间', dataIndex: 'created_at', render: (v: string) => new Date(v).toLocaleString('zh-CN') },
        ]}
      />
      <Button onClick={reload} style={{ marginTop: 12 }}>刷新</Button>
    </div>
  )
}

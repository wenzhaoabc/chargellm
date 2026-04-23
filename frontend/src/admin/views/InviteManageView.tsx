import { useCallback, useEffect, useState } from 'react'
import { App, Button, Form, Input, InputNumber, Modal, Popconfirm, Space, Switch, Table, Tag, Typography } from 'antd'
import {
  createAdminInvite,
  deleteAdminInvite,
  listAdminInvites,
  updateAdminInvite,
} from '@/api/admin'
import type { AdminInviteRow } from '@/api/types'

export function InviteManageView() {
  const { message } = App.useApp()
  const [items, setItems] = useState<AdminInviteRow[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [form] = Form.useForm()

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setItems(await listAdminInvites())
    } catch (err) {
      message.error('加载失败：' + (err instanceof Error ? err.message : '未知错误'))
    } finally {
      setLoading(false)
    }
  }, [message])

  useEffect(() => { reload() }, [reload])

  async function submitCreate() {
    const values = await form.validateFields()
    try {
      await createAdminInvite(values)
      message.success('已创建')
      setCreating(false)
      form.resetFields()
      reload()
    } catch (err) {
      message.error('创建失败：' + (err instanceof Error ? err.message : '未知错误'))
    }
  }

  async function toggleActive(row: AdminInviteRow) {
    try {
      await updateAdminInvite(row.id, { is_active: row.status !== 'active' })
      message.success(row.status === 'active' ? '已暂停' : '已启用')
      reload()
    } catch (err) {
      message.error('更新失败：' + (err instanceof Error ? err.message : '未知错误'))
    }
  }

  async function onDelete(id: number) {
    try {
      await deleteAdminInvite(id)
      message.success('已删除')
      reload()
    } catch (err) {
      message.error('删除失败：' + (err instanceof Error ? err.message : '未知错误'))
    }
  }

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>邀请码管理</Typography.Title>
        <Button type="primary" onClick={() => setCreating(true)}>新建邀请码</Button>
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        size="small"
        pagination={{ pageSize: 30 }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          { title: '编码', dataIndex: 'code', render: (v: string) => <Typography.Text code>{v}</Typography.Text> },
          { title: '名称', dataIndex: 'name' },
          { title: '使用 / 上限', render: (_, r) => `${r.usageCount} / ${r.usageLimit}` },
          { title: '人均配额', dataIndex: 'perUserQuota', width: 90 },
          { title: '到期', dataIndex: 'expiresAt', width: 120 },
          { title: '状态', dataIndex: 'status', width: 80, render: (v: string) => v === 'active' ? <Tag color="green">活跃</Tag> : <Tag>暂停</Tag> },
          {
            title: '操作',
            width: 180,
            render: (_, row) => (
              <Space size={4}>
                <Switch
                  size="small"
                  checked={row.status === 'active'}
                  onChange={() => toggleActive(row)}
                />
                <Popconfirm title="删除此邀请码?" onConfirm={() => onDelete(row.id)}>
                  <Button size="small" danger>删除</Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />
      <Modal
        open={creating}
        title="新建邀请码"
        onCancel={() => setCreating(false)}
        onOk={submitCreate}
      >
        <Form form={form} layout="vertical">
          <Form.Item label="名称" name="name" rules={[{ required: true }]}><Input placeholder="例如：内测批次 1" /></Form.Item>
          <Form.Item label="自定义编码" name="code">
            <Input placeholder="留空自动生成" />
          </Form.Item>
          <Form.Item label="最大使用次数" name="max_uses">
            <InputNumber min={1} max={10000} />
          </Form.Item>
          <Form.Item label="人均配额" name="per_user_quota">
            <InputNumber min={1} max={1000} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

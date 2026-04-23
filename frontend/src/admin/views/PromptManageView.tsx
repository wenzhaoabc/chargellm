import { useCallback, useEffect, useState } from 'react'
import { App, Button, Form, Input, InputNumber, Modal, Popconfirm, Space, Switch, Table, Tag, Typography } from 'antd'
import {
  createSystemPrompt,
  deleteSystemPrompt,
  listSystemPrompts,
  updateSystemPrompt,
  type SystemPrompt,
} from '@/api/adminExtra'

export function PromptManageView() {
  const { message } = App.useApp()
  const [items, setItems] = useState<SystemPrompt[]>([])
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState<SystemPrompt | null>(null)
  const [creating, setCreating] = useState(false)
  const [form] = Form.useForm()

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setItems(await listSystemPrompts())
    } catch (err) {
      message.error('加载失败：' + (err instanceof Error ? err.message : '未知错误'))
    } finally {
      setLoading(false)
    }
  }, [message])

  useEffect(() => {
    reload()
  }, [reload])

  function openCreate() {
    setEditing(null)
    setCreating(true)
    form.resetFields()
    form.setFieldsValue({ scope: 'default', is_active: true, sort_order: 0 })
  }

  function openEdit(row: SystemPrompt) {
    setEditing(row)
    setCreating(false)
    form.resetFields()
    form.setFieldsValue(row)
  }

  async function submit() {
    const values = await form.validateFields()
    try {
      if (editing) {
        await updateSystemPrompt(editing.id, values)
        message.success('已更新')
      } else {
        await createSystemPrompt(values)
        message.success('已创建')
      }
      setEditing(null)
      setCreating(false)
      reload()
    } catch (err) {
      message.error('提交失败：' + (err instanceof Error ? err.message : '未知错误'))
    }
  }

  async function onDelete(id: number) {
    try {
      await deleteSystemPrompt(id)
      message.success('已删除')
      reload()
    } catch (err) {
      message.error('删除失败：' + (err instanceof Error ? err.message : '未知错误'))
    }
  }

  return (
    <div>
      <Space style={{ marginBottom: 12 }} align="center">
        <Typography.Title level={4} style={{ margin: 0 }}>系统提示词</Typography.Title>
        <Button type="primary" onClick={openCreate}>新建</Button>
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        size="small"
        pagination={false}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          { title: 'scope', dataIndex: 'scope', width: 100, render: (v) => <Tag>{v}</Tag> },
          { title: '标题', dataIndex: 'title' },
          {
            title: '内容预览',
            dataIndex: 'content',
            render: (v: string) => <Typography.Text type="secondary">{v.length > 80 ? v.slice(0, 80) + '…' : v}</Typography.Text>,
          },
          { title: '排序', dataIndex: 'sort_order', width: 60 },
          { title: '激活', dataIndex: 'is_active', width: 60, render: (v: boolean) => (v ? <Tag color="green">是</Tag> : <Tag>否</Tag>) },
          {
            title: '操作',
            width: 160,
            render: (_, row) => (
              <Space size={4}>
                <Button size="small" onClick={() => openEdit(row)}>编辑</Button>
                <Popconfirm title="确认删除?" onConfirm={() => onDelete(row.id)}>
                  <Button size="small" danger>删除</Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />
      <Modal
        open={creating || editing !== null}
        title={editing ? '编辑系统提示词' : '新建系统提示词'}
        onCancel={() => { setCreating(false); setEditing(null) }}
        onOk={submit}
        width={720}
      >
        <Form form={form} layout="vertical">
          <Form.Item label="Scope" name="scope" rules={[{ required: true }]}>
            <Input placeholder="default" />
          </Form.Item>
          <Form.Item label="标题" name="title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="内容" name="content" rules={[{ required: true }]}>
            <Input.TextArea rows={10} />
          </Form.Item>
          <Form.Item label="排序" name="sort_order">
            <InputNumber min={0} />
          </Form.Item>
          <Form.Item label="启用" name="is_active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

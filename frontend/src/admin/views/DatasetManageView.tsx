import { useCallback, useEffect, useState } from 'react'
import { App, Button, Form, Input, Modal, Popconfirm, Space, Table, Tag, Typography, DatePicker } from 'antd'
import dayjs from 'dayjs'
import {
  deleteAdminDataset,
  importAdminDatasetFromMysql,
  listAdminDatasets,
} from '@/api/admin'
import type { BatteryExample } from '@/api/types'

export function DatasetManageView() {
  const { message } = App.useApp()
  const [items, setItems] = useState<BatteryExample[]>([])
  const [loading, setLoading] = useState(false)
  const [importing, setImporting] = useState(false)
  const [form] = Form.useForm()

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      setItems(await listAdminDatasets())
    } catch (err) {
      message.error('加载失败：' + (err instanceof Error ? err.message : '未知错误'))
    } finally {
      setLoading(false)
    }
  }, [message])

  useEffect(() => { reload() }, [reload])

  async function submitImport() {
    const values = await form.validateFields()
    const [start, end] = values.range as [dayjs.Dayjs, dayjs.Dayjs]
    try {
      await importAdminDatasetFromMysql({
        phone: values.phone,
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        title: values.title,
      })
      message.success('已导入')
      setImporting(false)
      form.resetFields()
      reload()
    } catch (err) {
      message.error('导入失败：' + (err instanceof Error ? err.message : '未知错误'))
    }
  }

  async function onDelete(id: number) {
    try {
      await deleteAdminDataset(id)
      message.success('已删除')
      reload()
    } catch (err) {
      message.error('删除失败：' + (err instanceof Error ? err.message : '未知错误'))
    }
  }

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>充电数据集</Typography.Title>
        <Button type="primary" onClick={() => setImporting(true)}>从 MySQL 导入</Button>
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        size="small"
        pagination={{ pageSize: 30 }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          { title: '名称', dataIndex: 'name' },
          { title: '类型', dataIndex: 'label', render: (v) => <Tag>{v}</Tag> },
          { title: '容量区间', dataIndex: 'capacityRange' },
          { title: '来源', dataIndex: 'source', render: (v) => <Tag color={v === 'mysql_import' ? 'gold' : 'blue'}>{v}</Tag> },
          {
            title: '操作',
            width: 100,
            render: (_, row) => (
              <Popconfirm title="删除此数据集?" onConfirm={() => onDelete(Number(row.datasetId || row.id))}>
                <Button size="small" danger>删除</Button>
              </Popconfirm>
            ),
          },
        ]}
      />
      <Modal
        open={importing}
        title="从 IOT MySQL 导入用户数据"
        onCancel={() => setImporting(false)}
        onOk={submitImport}
        width={520}
      >
        <Form form={form} layout="vertical">
          <Form.Item label="手机号" name="phone" rules={[{ required: true, pattern: /^\d{6,20}$/ }]}>
            <Input placeholder="如 13061947220" />
          </Form.Item>
          <Form.Item label="时间范围" name="range" rules={[{ required: true }]}>
            <DatePicker.RangePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="数据集名称" name="title">
            <Input placeholder="留空使用默认命名" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

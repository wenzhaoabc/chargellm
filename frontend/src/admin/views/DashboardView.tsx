import { useEffect, useState } from 'react'
import { App, Button, Card, Col, Row, Statistic, Typography } from 'antd'
import { listAdminInvites } from '@/api/admin'
import { listAdminConversations, listAdminUsersBackend } from '@/api/adminExtra'

export function DashboardView() {
  const { message } = App.useApp()
  const [stats, setStats] = useState({ users: 0, invites: 0, conversations: 0, loading: true })

  useEffect(() => {
    (async () => {
      try {
        const [users, invites, conversations] = await Promise.all([
          listAdminUsersBackend({ limit: 1 }),
          listAdminInvites(),
          listAdminConversations({ limit: 1 }),
        ])
        setStats({ users: users.total, invites: invites.length, conversations: conversations.total, loading: false })
      } catch (err) {
        message.error('概览加载失败：' + (err instanceof Error ? err.message : '未知错误'))
        setStats((s) => ({ ...s, loading: false }))
      }
    })()
  }, [message])

  return (
    <div>
      <Typography.Title level={4} style={{ marginBottom: 24 }}>
        平台概览
      </Typography.Title>
      <Row gutter={16}>
        <Col span={8}>
          <Card>
            <Statistic title="注册用户数" value={stats.users} loading={stats.loading} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="邀请码总数" value={stats.invites} loading={stats.loading} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="对话历史数" value={stats.conversations} loading={stats.loading} />
          </Card>
        </Col>
      </Row>
      <Card style={{ marginTop: 24 }} title="快速入口">
        <Button type="primary" href="#users">用户管理</Button>{' '}
        <Button href="#prompts">系统提示词</Button>{' '}
        <Button href="#welcome">欢迎语</Button>{' '}
        <Button href="#conversations">对话历史</Button>
      </Card>
    </div>
  )
}

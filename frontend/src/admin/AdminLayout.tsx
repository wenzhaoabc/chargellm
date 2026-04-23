import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Avatar, Button, Dropdown, Layout, Menu, Space, Typography } from 'antd'
import {
  BellOutlined,
  CommentOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  GiftOutlined,
  LogoutOutlined,
  MessageOutlined,
  SettingOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { setAdminToken } from '@/api/admin'
import { ConversationManageView } from './views/ConversationManageView'
import { DashboardView } from './views/DashboardView'
import { DatasetManageView } from './views/DatasetManageView'
import { InviteManageView } from './views/InviteManageView'
import { PromptManageView } from './views/PromptManageView'
import { UserManageView } from './views/UserManageView'
import { WelcomeManageView } from './views/WelcomeManageView'

type MenuKey =
  | 'dashboard'
  | 'users'
  | 'invites'
  | 'datasets'
  | 'conversations'
  | 'prompts'
  | 'welcome'

const MENU_ITEMS = [
  { key: 'dashboard', icon: <DashboardOutlined />, label: '平台概览' },
  { key: 'users', icon: <TeamOutlined />, label: '用户管理' },
  { key: 'invites', icon: <GiftOutlined />, label: '邀请码管理' },
  { key: 'datasets', icon: <DatabaseOutlined />, label: '充电数据集' },
  { key: 'conversations', icon: <MessageOutlined />, label: '对话历史' },
  { key: 'prompts', icon: <SettingOutlined />, label: '系统提示词' },
  { key: 'welcome', icon: <BellOutlined />, label: '欢迎语' },
]

export function AdminLayout() {
  const navigate = useNavigate()
  const [selected, setSelected] = useState<MenuKey>('dashboard')

  function onLogout() {
    setAdminToken('')
    navigate('/admin/login', { replace: true })
  }

  const content = useMemo(() => {
    switch (selected) {
      case 'dashboard':
        return <DashboardView />
      case 'users':
        return <UserManageView />
      case 'invites':
        return <InviteManageView />
      case 'datasets':
        return <DatasetManageView />
      case 'conversations':
        return <ConversationManageView />
      case 'prompts':
        return <PromptManageView />
      case 'welcome':
        return <WelcomeManageView />
      default:
        return null
    }
  }, [selected])

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Layout.Sider
        theme="light"
        width={220}
        style={{ borderRight: '1px solid #f0f0f0' }}
      >
        <div style={{ padding: '20px 16px', borderBottom: '1px solid #f0f0f0' }}>
          <Typography.Title level={4} style={{ margin: 0, color: '#1677ff' }}>
            ChargeLLM
          </Typography.Title>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            管理后台
          </Typography.Text>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selected]}
          onClick={({ key }) => setSelected(key as MenuKey)}
          items={MENU_ITEMS}
          style={{ borderRight: 0, paddingTop: 8 }}
        />
      </Layout.Sider>
      <Layout>
        <Layout.Header
          style={{
            background: '#fff',
            padding: '0 24px',
            borderBottom: '1px solid #f0f0f0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Typography.Text strong>
            {MENU_ITEMS.find((m) => m.key === selected)?.label}
          </Typography.Text>
          <Space>
            <Button type="link" size="small" onClick={() => navigate('/chat')}>
              返回对话
            </Button>
            <Dropdown
              menu={{
                items: [
                  { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: onLogout },
                ],
              }}
            >
              <Space style={{ cursor: 'pointer' }}>
                <Avatar icon={<UserOutlined />} size="small" />
                <Typography.Text>管理员</Typography.Text>
              </Space>
            </Dropdown>
          </Space>
        </Layout.Header>
        <Layout.Content style={{ padding: 24, background: '#f5f5f5' }}>
          <div style={{ background: '#fff', padding: 24, borderRadius: 8, minHeight: '100%' }}>
            {content}
          </div>
        </Layout.Content>
      </Layout>
    </Layout>
  )
}

// Hint to avoid "unused import" in minimal builds.
export const __icons = [CommentOutlined]

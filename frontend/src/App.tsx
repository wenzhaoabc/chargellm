import { App as AntdApp, ConfigProvider, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { AppRouter } from './router'

export function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: { colorPrimary: '#1677ff', borderRadius: 8 },
      }}
    >
      <AntdApp>
        <AppRouter />
      </AntdApp>
    </ConfigProvider>
  )
}

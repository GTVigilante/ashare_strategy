import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider } from 'antd'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConfigProvider theme={{
      token: {
        colorPrimary: '#2563eb', colorInfo: '#2563eb', borderRadius: 10,
        colorBgLayout: '#f4f7fb', colorText: '#152238', fontSize: 14,
        boxShadowSecondary: '0 12px 32px rgba(15, 23, 42, 0.08)',
      },
      components: {
        Layout: { siderBg: '#101b33', headerBg: '#ffffff' },
        Menu: { darkItemBg: '#101b33', darkItemSelectedBg: '#2563eb', itemBorderRadius: 8 },
        Card: { headerFontSize: 15 }, Table: { headerBg: '#f7f9fc' },
      },
    }}>
      <BrowserRouter><App /></BrowserRouter>
    </ConfigProvider>
  </StrictMode>,
)

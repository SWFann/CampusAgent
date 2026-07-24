import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'CampusAgent · 暨南大学智能校园管理与协作平台',
  description: '连接暨南大学校务管理、教师工作与学生校园生活的智能化平台',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body>
        {children}
      </body>
    </html>
  )
}
